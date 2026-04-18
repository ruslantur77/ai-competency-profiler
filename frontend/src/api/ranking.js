import { api } from './base';

export const getVacancyRankings = (vacancyId) => api.get(`/vacancies/${vacancyId}/rankings`);

export const getCandidateProfile = (candidateId) => api.get(`/candidates/${candidateId}/profile`);
