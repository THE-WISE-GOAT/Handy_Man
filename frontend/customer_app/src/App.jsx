import React from 'react';
import DefaultHomePage from '@shared/components/DefaultHomePage';

export default function App() {
  return (
    <div className="app-container">
      {/* Pulling the page directly out of your shared directory */}
      <DefaultHomePage />
    </div>
  );
}