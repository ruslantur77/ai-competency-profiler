export const CANDIDATE_STATUS_META = {
  pending: { label: 'Ожидает оценки', badge: 'pending' },
  completed: { label: 'Оценен', badge: 'completed' },
  failed: { label: 'Ошибка оценки', badge: 'failed' },
};

export const getCandidateStatusMeta = (status) =>
  CANDIDATE_STATUS_META[status] || CANDIDATE_STATUS_META.pending;
