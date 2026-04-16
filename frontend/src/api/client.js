import api from './base'

export { login, logout } from './auth'
export {
  listVacancies,
  createVacancy,
  getVacancy,
  getGraph,
  updateGraph,
  updateVacancyStatus,
} from './vacancies'
export { getSuggestions, decideSuggestion } from './suggestions'
export { getVacancyRankings, getCandidateProfile } from './ranking'
export { listTasks, getTask, rebuildTaskMapping, validateTaskMapping } from './tasks'
export { healthCheck } from './health'
export { normalizePageResponse, extractItems } from './adapters'
export { getErrorMessage } from './errors'

export default api
