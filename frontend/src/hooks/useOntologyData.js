import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getCategory,
  getCompetency,
  getSubCompetency,
  listCategories,
  listCompetencies,
  listSubCompetencies,
} from '../api/ontology';
import { getErrorMessage } from '../api/errors';

export const ENTITY_TYPE = {
  CATEGORY: 'category',
  COMPETENCY: 'competency',
  SUB_COMPETENCY: 'sub_competency',
};

export const EMPTY_SELECTION = { type: null, id: null };

export function useOntologyData({ notify }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [categories, setCategories] = useState([]);
  const [competencies, setCompetencies] = useState([]);
  const [subCompetencies, setSubCompetencies] = useState([]);

  const [selected, setSelected] = useState(EMPTY_SELECTION);
  const [selectedDetails, setSelectedDetails] = useState(null);

  const [expandedCategories, setExpandedCategories] = useState(() => new Set());
  const [expandedCompetencies, setExpandedCompetencies] = useState(() => new Set());

  const fetchOntology = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) setLoading(true);
      else setRefreshing(true);

      try {
        const [categoriesResponse, competenciesResponse, subCompetenciesResponse] =
          await Promise.all([listCategories(), listCompetencies(), listSubCompetencies()]);

        const nextCategories = Array.isArray(categoriesResponse.data)
          ? categoriesResponse.data
          : [];
        const nextCompetencies = Array.isArray(competenciesResponse.data)
          ? competenciesResponse.data
          : [];
        const nextSubCompetencies = Array.isArray(subCompetenciesResponse.data)
          ? subCompetenciesResponse.data
          : [];

        setCategories(nextCategories);
        setCompetencies(nextCompetencies);
        setSubCompetencies(nextSubCompetencies);

        setExpandedCategories(new Set(nextCategories.map((category) => category.id)));
        setExpandedCompetencies(new Set(nextCompetencies.map((competency) => competency.id)));
      } catch (error) {
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки онтологии' }), 'error');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [notify]
  );

  const refreshSelectedDetails = useCallback(
    async (selection) => {
      if (!selection?.type || !selection?.id) {
        setSelectedDetails(null);
        return;
      }

      try {
        if (selection.type === ENTITY_TYPE.CATEGORY) {
          const { data } = await getCategory(selection.id);
          setSelectedDetails(data);
          return;
        }

        if (selection.type === ENTITY_TYPE.COMPETENCY) {
          const { data } = await getCompetency(selection.id);
          setSelectedDetails(data);
          return;
        }

        const { data } = await getSubCompetency(selection.id);
        setSelectedDetails(data);
      } catch (error) {
        setSelectedDetails(null);
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки деталей' }), 'error');
      }
    },
    [notify]
  );

  useEffect(() => {
    fetchOntology();
  }, [fetchOntology]);

  useEffect(() => {
    refreshSelectedDetails(selected);
  }, [selected, refreshSelectedDetails]);

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories]
  );

  const competencyById = useMemo(
    () => new Map(competencies.map((competency) => [competency.id, competency])),
    [competencies]
  );

  const toggleCategory = useCallback((categoryId) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  }, []);

  const toggleCompetency = useCallback((competencyId) => {
    setExpandedCompetencies((prev) => {
      const next = new Set(prev);
      if (next.has(competencyId)) next.delete(competencyId);
      else next.add(competencyId);
      return next;
    });
  }, []);

  const refreshAndPreserveSelection = useCallback(async () => {
    await fetchOntology({ silent: true });
    await refreshSelectedDetails(selected);
  }, [fetchOntology, refreshSelectedDetails, selected]);

  const resetSelection = useCallback(() => {
    setSelected(EMPTY_SELECTION);
    setSelectedDetails(null);
  }, []);

  return {
    loading,
    refreshing,
    categories,
    competencies,
    subCompetencies,
    selected,
    selectedDetails,
    expandedCategories,
    expandedCompetencies,
    categoryById,
    competencyById,
    setSelected,
    fetchOntology,
    refreshAndPreserveSelection,
    toggleCategory,
    toggleCompetency,
    resetSelection,
  };
}
