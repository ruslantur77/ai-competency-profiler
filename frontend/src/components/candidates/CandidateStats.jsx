import React from 'react';

export default function CandidateStats({ total, counters }) {
  return (
    <div className="candidates-tab__stats">
      <div className="candidates-tab__stat">
        <span className="candidates-tab__stat-value">{total}</span>
        <span className="candidates-tab__stat-label">Всего</span>
      </div>
      <div className="candidates-tab__stat candidates-tab__stat--completed">
        <span className="candidates-tab__stat-value">{counters.completed}</span>
        <span className="candidates-tab__stat-label">Completed (page)</span>
      </div>
      <div className="candidates-tab__stat candidates-tab__stat--pending">
        <span className="candidates-tab__stat-value">{counters.pending}</span>
        <span className="candidates-tab__stat-label">Pending (page)</span>
      </div>
      <div className="candidates-tab__stat candidates-tab__stat--failed">
        <span className="candidates-tab__stat-value">{counters.failed}</span>
        <span className="candidates-tab__stat-label">Failed (page)</span>
      </div>
    </div>
  );
}
