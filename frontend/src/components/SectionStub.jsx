import React from 'react'
import AsyncState from './AsyncState'

export default function SectionStub({ title, hint }) {
  return (
    <AsyncState
      kind="empty"
      title={title}
      hint={hint || 'Раздел будет реализован в следующей итерации roadmap.'}
    />
  )
}
