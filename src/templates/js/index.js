document.addEventListener('DOMContentLoaded', () => {
  const socket = io();
  const gameIDPattern = /\/g\/(\d+)/;

  socket.on('reload', (gameID) => {
    const path = window.location.pathname;

    if (gameID == null) {
      if (path != '/') {
        return;
      }
    } else {
      const curGameID = path.match(gameIDPattern);
      if (curGameID != null && curGameID[1] !== gameID) {
        return;
      }
    }

    location.reload();
  });
});
