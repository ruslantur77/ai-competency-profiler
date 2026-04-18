// Временные заглушки вынесены из production API-слоя.
// Если потребуется legacy-интеграция, импортируйте адресно из этого файла.

export const deleteVacancy = () => Promise.reject(new Error('Недоступно'));
export const updateVacancy = () => Promise.reject(new Error('Недоступно'));
export const getVacancyStatus = () => Promise.reject(new Error('Недоступно'));
export const updateCategory = () => Promise.reject(new Error('Недоступно'));
export const addCategory = () => Promise.reject(new Error('Недоступно'));
export const deleteCategory = () => Promise.reject(new Error('Недоступно'));
export const aiFixCategory = () => Promise.reject(new Error('Недоступно'));
export const updateCompetency = () => Promise.reject(new Error('Недоступно'));
export const addCompetency = () => Promise.reject(new Error('Недоступно'));
export const deleteCompetency = () => Promise.reject(new Error('Недоступно'));
export const aiFixCompetencyFull = () => Promise.reject(new Error('Недоступно'));
export const updateSubCompetency = () => Promise.reject(new Error('Недоступно'));
export const addSubCompetency = () => Promise.reject(new Error('Недоступно'));
export const deleteSubCompetency = () => Promise.reject(new Error('Недоступно'));
export const aiFixCompetency = () => Promise.reject(new Error('Недоступно'));
