import React from 'react'

const STATS_CONFIG = [
  { key: 'total', label: 'Всего' },
  { key: 'ready', label: 'Ready', className: 'tasks-tab__stat--completed' },
  { key: 'pending', label: 'Pending', className: 'tasks-tab__stat--pending' },
  { key: 'draft', label: 'Draft', className: 'tasks-tab__stat--draft' },
  { key: 'failed', label: 'Failed', className: 'tasks-tab__stat--failed' },
]

export default function TaskStats({ counters }) {
  return (
    <div className="tasks-tab__stats">
      {STATS_CONFIG.map((item) => (
        <div key={item.key} className={`tasks-tab__stat ${item.className || ''}`.trim()}>
          <span className="tasks-tab__stat-value">{counters[item.key] ?? 0}</span>
          <span className="tasks-tab__stat-label">{item.label}</span>
        </div>
      ))}
    </div>
  )
}
