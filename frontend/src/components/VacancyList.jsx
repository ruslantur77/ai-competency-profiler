// frontend/src/components/VacancyList.jsx
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle, FileEdit } from 'lucide-react';
import { createVacancy } from '../api/vacancies';
import { getErrorMessage } from '../api/errors';
import {
  canAccessAdminUsers,
  canAccessCandidates,
  canAccessOntology,
  canAccessRanking,
  canAccessReviewQueue,
  canAccessTasks,
  canAccessVacancies,
  canCreateVacancy,
} from '../api/roles';
import CreateVacancyDialog from './CreateVacancyDialog';
import RankingTab from './RankingTab';
import TasksTab from './TasksTab';
import AsyncState from './AsyncState';
import OntologyTab from './OntologyTab';
import ConfirmDialog from './ConfirmDialog';
import CandidatesTab from './CandidatesTab';
import AdminUsersTab from './AdminUsersTab';
import useVacanciesData from '../hooks/useVacanciesData';
import useVacancyLifecycle from '../hooks/useVacancyLifecycle';
import VacancyListHeader from './vacancy-list/VacancyListHeader';
import VacancyTabs from './vacancy-list/VacancyTabs';
import VacancyModeSwitch from './vacancy-list/VacancyModeSwitch';
import RecentlyDeletedPanel from './vacancy-list/RecentlyDeletedPanel';
import VacancyCardsGrid from './vacancy-list/VacancyCardsGrid';
import './VacancyList.css';

const STATUS_CONFIG = {
  pending: {
    label: 'Извлечение компетенций...',
    badge: 'extracting',
    icon: (size) => <Loader2 size={size} className="spin" />,
  },
  draft: {
    label: 'Ожидает валидации',
    badge: 'draft',
    icon: (size) => <FileEdit size={size} />,
  },
  ready: {
    label: 'Граф финализирован',
    badge: 'ready',
    icon: (size) => <CheckCircle size={size} />,
  },
  failed: {
    label: 'Ошибка обработки, попробуйте позже',
    badge: 'failed',
    icon: (size) => <AlertCircle size={size} />,
  },
};

export default function VacancyList({ notify, onLogout, role, currentUser }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState('vacancies');
  const [creating, setCreating] = useState(false);
  const [vacancyMode, setVacancyMode] = useState('all');
  const [rankingNavigationTarget, setRankingNavigationTarget] = useState(null);
  const pollCycleRef = useRef(0);
  const canSeeVacancies = canAccessVacancies(role);
  const canSeeTasks = canAccessTasks(role);
  const canSeeRanking = canAccessRanking(role);
  const canSeeOntology = canAccessOntology(role);
  const canSeeCandidates = canAccessCandidates(role);
  const canSeeAdminUsers = canAccessAdminUsers(role);
  const canSeeReviewQueue = canAccessReviewQueue(role);
  const canCreate = canCreateVacancy(role);
  const effectiveVacancyMode = canSeeReviewQueue ? vacancyMode : 'all';
  const { vacancies, allVacancies, loading, fetchVacancies, setLoading, setVacancies } =
    useVacanciesData({ notify, vacancyMode: effectiveVacancyMode });
  const {
    confirmAction,
    recentlyDeleted,
    setConfirmAction,
    openDeleteConfirm,
    openHardDeleteConfirm,
    handleConfirmAction,
    handleRestore,
  } = useVacancyLifecycle({ notify, fetchVacancies });
  const tabs = useMemo(
    () => [
      ...(canSeeVacancies  ? [{ id: 'vacancies',   label: '📋 Вакансии' }]    : []),
      ...(canSeeOntology   ? [{ id: 'ontology',    label: '🧩 Онтология' }]   : []),
      ...(canSeeTasks      ? [{ id: 'tasks',        label: '📝 Задания' }]     : []),
      ...(canSeeCandidates ? [{ id: 'candidates',  label: '👤 Кандидаты' }]   : []),
      ...(canSeeRanking    ? [{ id: 'ranking',     label: '🏆 Ранжирование' }] : []),
      ...(canSeeAdminUsers ? [{ id: 'admin-users', label: '🛡️ Пользователи' }] : []),
    ],
    [canSeeVacancies, canSeeOntology, canSeeTasks, canSeeRanking, canSeeCandidates, canSeeAdminUsers]
  );
  const resolvedActiveTab = tabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : tabs[0]?.id || 'vacancies';

  useEffect(() => {
    if (!canSeeVacancies) {
      setVacancies([]);
      setLoading(false);
      return;
    }
    fetchVacancies();
  }, [fetchVacancies, canSeeVacancies, setLoading, setVacancies]);

  useEffect(() => {
    if (!canSeeVacancies) return;
    fetchVacancies();
  }, [location.key, canSeeVacancies]); // eslint-disable-line react-hooks/exhaustive-deps

  // Умный polling: только когда есть pending, вкладка видима и пользователь в табе вакансий.
  useEffect(() => {
    const hasPending = allVacancies.some((v) => v.status === 'pending')
    if (
      !canSeeVacancies ||
      effectiveVacancyMode !== 'all' ||
      !hasPending ||
      resolvedActiveTab !== 'vacancies'
    ) {
      pollCycleRef.current = 0;
      return;
    }

    if (document.hidden) return;

    const cycle = pollCycleRef.current + 1;
    pollCycleRef.current = cycle;
    const delayMs = Math.min(15000, 3000 + cycle * 1000);
    if (cycle > 40) return;

    const timer = setTimeout(() => {
      fetchVacancies({ silent: true });
    }, delayMs);
    return () => clearTimeout(timer);
  }, [vacancies, fetchVacancies, resolvedActiveTab, canSeeVacancies, effectiveVacancyMode]);

  const handleCreate = async (data) => {
    try {
      if (!canCreate) {
        notify('Недостаточно прав для создания вакансии', 'error');
        return;
      }
      await createVacancy(data);
      setCreating(false);
      await fetchVacancies();
      notify(`✅ Вакансия "${data.name}" создана, запущено извлечение компетенций`);
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания вакансии' }), 'error');
    }
  };

  const handleOpen = (vacancy) => {
    if (vacancy.status === 'ready' || vacancy.status === 'draft') {
      navigate(`/vacancy/${vacancy.id}`);
    }
  };

  const handleOpenCandidateVacancy = (vacancyId) => {
    navigate(`/vacancy/${vacancyId}`);
  };

  const handleOpenCandidateRanking = ({ vacancyId, candidateId }) => {
    setRankingNavigationTarget({
      vacancyId,
      candidateId,
      token: Date.now(),
    });
    setActiveTab('ranking');
  };

  const handleLogout = async () => {
    try {
      await onLogout();
    } catch {
      // logout имеет централизованный fallback в App; здесь не дублируем уведомление
    }
  };

  const vacancyUniverse = allVacancies.length > 0 ? allVacancies : vacancies;

  // Только ready вакансии для ранжирования
  const readyVacancies = vacancyUniverse.filter((v) => v.status === 'ready');

  return (
    <div className="vacancy-list">
      {/* ===== HEADER ===== */}
      <VacancyListHeader
        activeTab={resolvedActiveTab}
        canCreate={canCreate}
        onCreate={() => setCreating(true)}
        onLogout={handleLogout}
      />

      {/* ===== ТАБЫ ===== */}
      <VacancyTabs tabs={tabs} activeTab={resolvedActiveTab} onTabChange={setActiveTab} />

      {/* ===== КОНТЕНТ ===== */}
      <div className="vacancy-list__content">
        {/* ВАКАНСИИ */}
        {resolvedActiveTab === 'vacancies' && (
          <>
            <VacancyModeSwitch
              vacancyMode={effectiveVacancyMode}
              canSeeReviewQueue={canSeeReviewQueue}
              onModeChange={setVacancyMode}
            />

            {loading ? (
              <AsyncState kind="loading" title="Загрузка вакансий..." />
            ) : vacancies.length === 0 ? (
              <AsyncState
                kind="empty"
                title="Вакансий пока нет"
                hint={
                  canCreate
                    ? 'Создайте первую вакансию для формирования профиля компетенций кандидата'
                    : 'Вакансий пока нет'
                }
              />
            ) : (
              <>
                <RecentlyDeletedPanel
                  items={recentlyDeleted}
                  onRestore={handleRestore}
                  onHardDelete={openHardDeleteConfirm}
                />

                <VacancyCardsGrid
                  vacancies={vacancies}
                  statusConfig={STATUS_CONFIG}
                  onOpen={handleOpen}
                  onDelete={openDeleteConfirm}
                />

              </>
            )}
          </>
        )}

        {resolvedActiveTab === 'vacancies' && confirmAction && (
          <ConfirmDialog
            title={confirmAction.title}
            message={confirmAction.message}
            confirmLabel={confirmAction.confirmLabel}
            requireText={confirmAction.requireText}
            requireHint={confirmAction.requireHint}
            onConfirm={handleConfirmAction}
            onCancel={() => setConfirmAction(null)}
          />
        )}

        {/* ЗАДАНИЯ */}
        {resolvedActiveTab === 'tasks' && <TasksTab notify={notify} />}

        {/* РАНЖИРОВАНИЕ */}
        {resolvedActiveTab === 'ranking' && (
          <RankingTab
            vacancies={readyVacancies}
            notify={notify}
            navigationTarget={rankingNavigationTarget}
          />
        )}

        {/* ОНТОЛОГИЯ */}
        {resolvedActiveTab === 'ontology' && <OntologyTab notify={notify} />}

        {/* КАНДИДАТЫ */}
        {resolvedActiveTab === 'candidates' && (
          <CandidatesTab
            notify={notify}
            vacancies={vacancyUniverse}
            onOpenVacancy={handleOpenCandidateVacancy}
            onOpenRanking={handleOpenCandidateRanking}
          />
        )}

        {/* ADMIN USERS */}
        {resolvedActiveTab === 'admin-users' && (
          <AdminUsersTab notify={notify} currentUserId={currentUser?.id || null} />
        )}
      </div>

      {creating && canCreate && (
        <CreateVacancyDialog onClose={() => setCreating(false)} onCreate={handleCreate} />
      )}
    </div>
  );
}
