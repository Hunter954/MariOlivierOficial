document.addEventListener('DOMContentLoaded', () => {
  const copyButton = document.querySelector('.copy-link');
  if (copyButton) {
    copyButton.addEventListener('click', async () => {
      const value = copyButton.dataset.copy;
      try {
        await navigator.clipboard.writeText(value);
        copyButton.textContent = 'Link copiado';
      } catch (error) {
        copyButton.textContent = 'Falha ao copiar';
      }
    });
  }

  const video = document.getElementById('episode-player');
  if (!video) return;

  const episodeId = video.dataset.episodeId;
  const savedResume = window.__resumeAt || 0;
  let lastSentSecond = 0;

  video.addEventListener('loadedmetadata', () => {
    if (savedResume > 5 && savedResume < video.duration - 10) {
      video.currentTime = savedResume;
    }
  });

  const persistProgress = async (completed = false) => {
    if (!episodeId) return;
    const secondsWatched = Math.floor(video.currentTime || 0);
    if (!completed && Math.abs(secondsWatched - lastSentSecond) < 10) return;
    lastSentSecond = secondsWatched;

    try {
      await fetch(`/api/progress/${episodeId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seconds_watched: secondsWatched, completed }),
      });
    } catch (error) {
      console.error('Erro ao salvar progresso', error);
    }
  };

  video.addEventListener('timeupdate', () => {
    if (Math.floor(video.currentTime) % 15 === 0) {
      persistProgress(false);
    }
  });

  video.addEventListener('pause', () => persistProgress(false));
  video.addEventListener('ended', () => persistProgress(true));
  window.addEventListener('beforeunload', () => persistProgress(false));
});
