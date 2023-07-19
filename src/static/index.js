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
