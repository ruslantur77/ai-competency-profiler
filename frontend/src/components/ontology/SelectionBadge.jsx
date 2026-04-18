import React from 'react'

export default function SelectionBadge({ selected }) {
  if (!selected?.type || !selected?.id) return null

  return (
    <span className="ontology__selection-badge">
      {selected.type}: {selected.id}
    </span>
  )
}
