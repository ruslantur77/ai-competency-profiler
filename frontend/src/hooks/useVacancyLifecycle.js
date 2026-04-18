import { useState } from 'react';
import {
  updateVacancyStatus,
  deleteVacancy,
  restoreVacancy,
  hardDeleteVacancy,
} from '../api/vacancies';
import { getErrorMessage } from '../api/errors';

export default function useVacancyLifecycle({ notify, fetchVacancies }) {
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [recentlyDeleted, setRecentlyDeleted] = useState([]);

  const handleStatusChange = async (vacancyId, nextStatus) => {
    setUpdatingStatusId(vacancyId);
    try {
      await updateVacancyStatus(vacancyId, nextStatus);
      notify('Статус вакансии обновлен');
      await fetchVacancies({ silent: true });
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления статуса' }), 'error');
    } finally {
      setUpdatingStatusId(null);
    }
  };

  const openDeleteConfirm = (vacancy) => {
    setConfirmAction({
      type: 'delete',
      vacancy,
      title: 'Удаление вакансии',
      message: `Удалить вакансию "${vacancy.name}"? Вакансию можно будет восстановить из панели удаленных.`,
      confirmLabel: 'Удалить',
    });
  };

  const openHardDeleteConfirm = (vacancy) => {
    setConfirmAction({
      type: 'hard-delete',
      vacancy,
      title: 'Полное удаление вакансии',
      message: `Полностью удалить "${vacancy.name}" без возможности восстановления?`,
      confirmLabel: 'Удалить навсегда',
      requireText: vacancy.name,
      requireHint: `Для подтверждения введите точное название: ${vacancy.name}`,
    });
  };

  const handleConfirmAction = async () => {
    if (!confirmAction?.vacancy) return;

    const { type, vacancy } = confirmAction;
    try {
      if (type === 'delete') {
        await deleteVacancy(vacancy.id);
        setRecentlyDeleted((prev) =>
          [
            { id: vacancy.id, name: vacancy.name, deletedAt: new Date().toISOString() },
            ...prev.filter((item) => item.id !== vacancy.id),
          ].slice(0, 5)
        );
        notify('Вакансия удалена');
      } else if (type === 'hard-delete') {
        await hardDeleteVacancy(vacancy.id);
        setRecentlyDeleted((prev) => prev.filter((item) => item.id !== vacancy.id));
        notify('Вакансия удалена без возможности восстановления');
      }
      setConfirmAction(null);
      await fetchVacancies({ silent: true });
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка выполнения операции' }), 'error');
    }
  };

  const handleRestore = async (vacancy) => {
    try {
      await restoreVacancy(vacancy.id);
      notify(`Вакансия "${vacancy.name}" восстановлена`);
      setRecentlyDeleted((prev) => prev.filter((item) => item.id !== vacancy.id));
      await fetchVacancies({ silent: true });
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка восстановления вакансии' }), 'error');
    }
  };

  return {
    updatingStatusId,
    confirmAction,
    recentlyDeleted,
    setConfirmAction,
    openDeleteConfirm,
    openHardDeleteConfirm,
    handleConfirmAction,
    handleRestore,
    handleStatusChange,
  };
}
