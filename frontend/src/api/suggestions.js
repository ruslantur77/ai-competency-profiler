import { api } from './base';

export const getSuggestions = (vacancyId) => api.get(`/vacancies/${vacancyId}/suggestions`);

export const decideSuggestion = (vacancyId, suggestionId, status) =>
  api.post(`/vacancies/${vacancyId}/suggestions/decision`, {
    suggestion_id: suggestionId,
    status,
  });

export const decideSuggestionsBulk = (vacancyId, decisions) =>
  api.post(`/vacancies/${vacancyId}/suggestions/decisions`, { decisions });
