class SermonPlayer {
    constructor(audioElement) {
        this.audio = audioElement;
        this.sermonId = audioElement.dataset.sermonId;
        this.fingerprint = null;
        this.saveInterval = null;
        this.progressLoaded = false;
        
        this.init();
    }

    async init() {
        this.fingerprint = await BrowserFingerprint.get();
        await this.loadProgress();
        this.attachEventListeners();
        this.addSpeedControl();
    }

    async loadProgress() {
        if (this.progressLoaded) return;
        
        try {
            const response = await fetch(`/api/progress/${this.sermonId}/?fingerprint=${this.fingerprint}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.position > 0) {
                this.audio.currentTime = data.position;
                this.progressLoaded = true;
                this.showResumeNotification(data.position);
            }
        } catch (error) {
            console.error('Failed to load progress:', error);
        }
    }

    showResumeNotification(position) {
        const minutes = Math.floor(position / 60);
        const seconds = Math.floor(position % 60);
        const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded shadow-lg z-50';
        notification.textContent = `Resuming from ${timeStr}`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    attachEventListeners() {
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('ended', () => this.onEnded());
        
        this.audio.addEventListener('loadedmetadata', () => {
            if (!this.progressLoaded) {
                this.loadProgress();
            }
        });
    }

    onPlay() {
        this.startSavingProgress();
    }

    onPause() {
        this.stopSavingProgress();
        this.saveProgress();
    }

    onTimeUpdate() {
    }

    onEnded() {
        this.stopSavingProgress();
        this.saveProgress(0);
    }

    startSavingProgress() {
        if (this.saveInterval) return;
        
        this.saveInterval = setInterval(() => {
            this.saveProgress();
        }, 5000);
    }

    stopSavingProgress() {
        if (this.saveInterval) {
            clearInterval(this.saveInterval);
            this.saveInterval = null;
        }
    }

    async saveProgress(position = null) {
        const currentPosition = position !== null ? position : Math.floor(this.audio.currentTime);
        
        try {
            const response = await fetch('/api/progress/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    fingerprint: this.fingerprint,
                    sermon_id: this.sermonId,
                    position: currentPosition
                })
            });
            
            const data = await response.json();
            if (data.status !== 'success') {
                console.error('Failed to save progress');
            }
        } catch (error) {
            console.error('Error saving progress:', error);
        }
    }

    addSpeedControl() {
        const container = this.audio.parentElement;
        
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'flex items-center gap-4 mt-2';
        
        const speedLabel = document.createElement('label');
        speedLabel.className = 'text-sm font-medium text-gray-700';
        speedLabel.textContent = 'Playback Speed:';
        
        const speedSelect = document.createElement('select');
        speedSelect.className = 'border rounded px-2 py-1 text-sm';
        
        const speeds = [
            { value: 0.5, label: '0.5x' },
            { value: 0.75, label: '0.75x' },
            { value: 1.0, label: '1x (Normal)' },
            { value: 1.25, label: '1.25x' },
            { value: 1.5, label: '1.5x' },
            { value: 1.75, label: '1.75x' },
            { value: 2.0, label: '2x' }
        ];
        
        speeds.forEach(speed => {
            const option = document.createElement('option');
            option.value = speed.value;
            option.textContent = speed.label;
            if (speed.value === 1.0) {
                option.selected = true;
            }
            speedSelect.appendChild(option);
        });
        
        speedSelect.addEventListener('change', (e) => {
            this.audio.playbackRate = parseFloat(e.target.value);
            localStorage.setItem('preferredPlaybackSpeed', e.target.value);
        });
        
        const savedSpeed = localStorage.getItem('preferredPlaybackSpeed');
        if (savedSpeed) {
            speedSelect.value = savedSpeed;
            this.audio.playbackRate = parseFloat(savedSpeed);
        }
        
        const progressDiv = document.createElement('div');
        progressDiv.className = 'flex-1 text-sm text-gray-600';
        progressDiv.id = `progress-${this.sermonId}`;
        
        controlsDiv.appendChild(speedLabel);
        controlsDiv.appendChild(speedSelect);
        controlsDiv.appendChild(progressDiv);
        
        container.appendChild(controlsDiv);
        
        this.updateProgressDisplay();
        this.audio.addEventListener('timeupdate', () => this.updateProgressDisplay());
    }

    updateProgressDisplay() {
        const progressDiv = document.getElementById(`progress-${this.sermonId}`);
        if (!progressDiv) return;
        
        const current = this.formatTime(this.audio.currentTime);
        const duration = this.formatTime(this.audio.duration);
        
        if (isFinite(this.audio.duration)) {
            progressDiv.textContent = `${current} / ${duration}`;
        } else {
            progressDiv.textContent = current;
        }
    }

    formatTime(seconds) {
        if (!isFinite(seconds)) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const audioElements = document.querySelectorAll('audio[data-sermon-id]');
    audioElements.forEach(audio => {
        new SermonPlayer(audio);
    });
});
