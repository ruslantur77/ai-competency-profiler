// VacancyModeSwitch.jsx
const MODES = [
  { id: 'all',     label: 'Все вакансии' },
  { id: 'pending', label: 'Обрабатывается' },
  { id: 'draft',   label: 'Ожидают проверки' },
  { id: 'ready',   label: 'Финализированы' },
  { id: 'failed',  label: 'Ошибка обработки' },
]

export default function VacancyModeSwitch({ vacancyMode, onModeChange }) {
  return (
    <div className="vacancy-list__mode">
      {MODES.map(mode => (
        <button
          key={mode.id}
          className={`vacancy-list__mode-btn ${vacancyMode === mode.id ? 'is-active' : ''}`}
          onClick={() => onModeChange(mode.id)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  )
}