document.addEventListener('DOMContentLoaded', () => {
  const socket = io();
  const gameIDPattern = /\/g\/(\d+)/;

  socket.on('reload', (gameID) => {
    const path = window.location.pathname;

    if (path === '/') {
      if (gameID == null) {
        window.location.reload();
      }
    } else {
      const curGameID = path.match(gameIDPattern);
      if (curGameID != null && curGameID[1] === gameID) {
        window.location.reload();
      }
    }
  });
});

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-copy]');
  if (button == null) {
    return;
  }

  const label = button.textContent;
  const done = (text) => {
    button.textContent = text;
    setTimeout(() => { button.textContent = label; }, 1500);
  };

  if (navigator.clipboard == null) {
    window.prompt('Copy this:', button.dataset.copy);
    return;
  }

  navigator.clipboard.writeText(button.dataset.copy)
    .then(() => done('Copied!'))
    .catch(() => window.prompt('Copy this:', button.dataset.copy));
});
