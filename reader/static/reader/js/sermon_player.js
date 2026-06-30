class SermonPlayer {
    constructor(audioElement) {
        this.audio = audioElement;
        this.sermonId = audioElement.dataset.sermonId;
        this.fingerprint = null;
        this.saveInterval = null;
        this.progressLoaded = false;
        this.pendingPosition = null;
        
        this.init();
    }

    async init() {
        this.attachEventListeners();
        this.addSpeedControl();
        this.fingerprint = await BrowserFingerprint.get();
        console.log('[SermonPlayer] Fingerprint ready:', this.fingerprint.substring(0, 16) + '...');
        await this.loadProgress();
    }

    async loadProgress() {
        if (this.progressLoaded) return;
        
        try {
            console.log('[SermonPlayer] Loading progress for sermon', this.sermonId);
            const response = await fetch(`/api/progress/${this.sermonId}/?fingerprint=${this.fingerprint}`);
            const data = await response.json();
            console.log('[SermonPlayer] Progress response:', data, 'readyState:', this.audio.readyState);
            
            if (data.status === 'success' && data.position > 0) {
                this.pendingPosition = data.position;
                this.updateProgressDisplay();
                this.applyPendingPosition();
            } else {
                console.log('[SermonPlayer] No saved progress or position is 0');
            }
        } catch (error) {
            console.error('[SermonPlayer] Failed to load progress:', error);
        }
    }

    applyPendingPosition() {
        if (this.pendingPosition === null) return;
        
        console.log('[SermonPlayer] Applying position', this.pendingPosition, 'readyState:', this.audio.readyState);
        
        if (this.audio.readyState >= 1) {
            this.audio.currentTime = this.pendingPosition;
            const target = this.pendingPosition;
            this.progressLoaded = true;
            this.pendingPosition = null;
            
            setTimeout(() => {
                if (this.audio.currentTime === 0 && target > 0) {
                    console.log('[SermonPlayer] Browser reset to 0, retrying...');
                    this.audio.currentTime = target;
                    setTimeout(() => {
                        console.log('[SermonPlayer] After retry, currentTime is now:', this.audio.currentTime);
                    }, 100);
                } else {
                    console.log('[SermonPlayer] Position applied, currentTime is now:', this.audio.currentTime);
                }
            }, 200);
        } else {
            console.log('[SermonPlayer] Audio not ready, waiting for canplay...');
        }
    }

    attachEventListeners() {
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());
        this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audio.addEventListener('ended', () => this.onEnded());
        
        this.audio.addEventListener('canplay', () => {
            this.applyPendingPosition();
        });
        this.audio.addEventListener('loadedmetadata', () => {
            this.applyPendingPosition();
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
        
        const doSave = () => {
            if (this.fingerprint) {
                this.saveProgress();
            } else {
                console.log('Waiting for fingerprint before saving...');
            }
        };
        
        doSave();
        this.saveInterval = setInterval(doSave, 5000);
    }

    stopSavingProgress() {
        if (this.saveInterval) {
            clearInterval(this.saveInterval);
            this.saveInterval = null;
        }
    }

    async saveProgress(position = null) {
        const currentPosition = position !== null ? position : Math.floor(this.audio.currentTime);
        
        if (!this.fingerprint) {
            console.error('Fingerprint not ready, cannot save progress');
            return;
        }
        
        try {
            const response = await fetch('/api/progress/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    fingerprint: this.fingerprint,
                    sermon_id: this.sermonId,
                    position: currentPosition
                })
            });
            
            if (!response.ok) {
                const text = await response.text();
                console.error(`Save progress failed: ${response.status} ${response.statusText}`);
                console.error('Response:', text.substring(0, 200));
                return;
            }
            
            const data = await response.json();
            if (data.status !== 'success') {
                console.error('Failed to save progress:', data);
            } else {
                console.log(`Progress saved: ${currentPosition}s`);
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
        
        let displayTime = this.audio.currentTime;
        if (displayTime === 0 && this.pendingPosition !== null) {
            displayTime = this.pendingPosition;
        }
        
        const current = this.formatTime(displayTime);
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
        
        if (!cookieValue && name === 'csrftoken') {
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                cookieValue = metaTag.getAttribute('content');
            }
        }
        
        return cookieValue;
    }
}

const sermonPlayers = [];

document.addEventListener('DOMContentLoaded', () => {
    const audioElements = document.querySelectorAll('audio[data-sermon-id]');
    audioElements.forEach(audio => {
        sermonPlayers.push(new SermonPlayer(audio));
    });
});

window.addEventListener('beforeunload', () => {
    sermonPlayers.forEach(player => {
        if (player.fingerprint && !player.audio.paused) {
            fetch('/api/progress/save/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': player.getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    fingerprint: player.fingerprint,
                    sermon_id: player.sermonId,
                    position: Math.floor(player.audio.currentTime)
                }),
                keepalive: true
            }).catch(() => {});
        }
    });
});
