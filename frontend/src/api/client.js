import api from './base'

export { login, logout } from './auth'
export {
  listVacancies,
  listVacanciesForReview,
  createVacancy,
  getVacancy,
  getGraph,
  updateGraph,
  finalizeVacancyGraph,
  updateVacancyStatus,
  deleteVacancy,
  restoreVacancy,
  hardDeleteVacancy,
} from './vacancies'
export { getSuggestions, decideSuggestion } from './suggestions'
export { getVacancyRankings, getCandidateProfile } from './ranking'
export {
  listTasks,
  getTask,
  updateTaskGraph,
  finalizeTaskGraph,
  updateTaskStatus,
} from './tasks'
export {
  listCategories,
  getCategory,
  createCategory,
  updateCategory,
  deleteCategory,
  listCompetencies,
  getCompetency,
  createCompetency,
  updateCompetency,
  deleteCompetency,
  listSubCompetencies,
  getSubCompetency,
  createSubCompetency,
  updateSubCompetency,
  deleteSubCompetency,
} from './ontology'
export { healthCheck } from './health'
export { normalizePageResponse, extractItems } from './adapters'
export { getErrorMessage } from './errors'

export default api
