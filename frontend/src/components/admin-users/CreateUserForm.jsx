import React, { useState } from 'react';
import { UserPlus } from 'lucide-react';

const ROLE_OPTIONS = ['admin', 'expert', 'hr', 'system'];

export default function CreateUserForm({ onSubmit, creating }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('hr');

  const isValid = email.trim().length > 0 && password.trim().length >= 8;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!isValid || creating) return;
    onSubmit({
      email: email.trim(),
      password,
      role,
    });
    setEmail('');
    setPassword('');
    setRole('hr');
  };

  return (
    <form className="admin-users__create" onSubmit={handleSubmit}>
      <h3>
        <UserPlus size={16} />
        Создать пользователя
      </h3>
      <div className="admin-users__create-grid">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Пароль (мин. 8 символов)"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />
        <select value={role} onChange={(event) => setRole(event.target.value)}>
          {ROLE_OPTIONS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button type="submit" className="btn-primary" disabled={!isValid || creating}>
          Создать
        </button>
      </div>
    </form>
  );
}
