// Add page - handles both sets and individual minifigures
document.addEventListener("DOMContentLoaded", () => {
  // Get template data from data attributes
  const addContainer = document.getElementById('add-set');
  if (!addContainer) return;

  // Read data from data attributes
  const templateData = {
    path: addContainer.dataset.path,
    namespace: addContainer.dataset.namespace,
    messages: {
      COMPLETE: addContainer.dataset.msgComplete,
      FAIL: addContainer.dataset.msgFail,
      IMPORT_SET: addContainer.dataset.msgImportSet,
      LOAD_SET: addContainer.dataset.msgLoadSet,
      PROGRESS: addContainer.dataset.msgProgress,
      SET_LOADED: addContainer.dataset.msgSetLoaded,
      IMPORT_MINIFIGURE: addContainer.dataset.msgImportMinifigure,
      LOAD_MINIFIGURE: addContainer.dataset.msgLoadMinifigure,
      MINIFIGURE_LOADED: addContainer.dataset.msgMinifigureLoaded,
    }
  };

  // Default: create set socket
  const setSocket = new BrickSetSocket(
    'add',
    templateData.path,
    templateData.namespace,
    {
      COMPLETE: templateData.messages.COMPLETE,
      FAIL: templateData.messages.FAIL,
      IMPORT_SET: templateData.messages.IMPORT_SET,
      LOAD_SET: templateData.messages.LOAD_SET,
      PROGRESS: templateData.messages.PROGRESS,
      SET_LOADED: templateData.messages.SET_LOADED,
    },
    false,
    false
  );

  // Override the execute method to check for minifigures
  const originalExecute = setSocket.execute.bind(setSocket);
  let minifigSocket = null;

  setSocket.execute = function() {
    const inputValue = document.getElementById('add-set').value.trim();

    if (inputValue.startsWith('fig-') || inputValue.match(/^fig\d/i)) {
      // It's a minifigure - create minifig socket if needed and execute when ready
      if (!minifigSocket) {
        minifigSocket = new BrickMinifigureSocket(
          'add',
          templateData.path,
          templateData.namespace,
          {
            COMPLETE: templateData.messages.COMPLETE,
            FAIL: templateData.messages.FAIL,
            IMPORT_MINIFIGURE: templateData.messages.IMPORT_MINIFIGURE,
            LOAD_MINIFIGURE: templateData.messages.LOAD_MINIFIGURE,
            MINIFIGURE_LOADED: templateData.messages.MINIFIGURE_LOADED,
            PROGRESS: templateData.messages.PROGRESS,
          }
        );

        // Wait for socket to connect before executing
        const checkConnection = setInterval(() => {
          if (minifigSocket.socket && minifigSocket.socket.connected) {
            clearInterval(checkConnection);
            minifigSocket.execute();
          }
        }, 100);
      } else {
        minifigSocket.execute();
      }
    } else {
      // It's a set - use original execute
      originalExecute();
    }
  };
});
