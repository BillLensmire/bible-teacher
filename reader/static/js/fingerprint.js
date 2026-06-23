class BrowserFingerprint {
    constructor() {
        this.fingerprint = null;
    }

    async generate() {
        if (this.fingerprint) {
            return this.fingerprint;
        }

        const components = await this.getComponents();
        const fingerprintString = JSON.stringify(components);
        this.fingerprint = await this.hashString(fingerprintString);
        
        localStorage.setItem('browserFingerprint', this.fingerprint);
        return this.fingerprint;
    }

    async getComponents() {
        const components = {
            userAgent: navigator.userAgent,
            language: navigator.language,
            colorDepth: screen.colorDepth,
            deviceMemory: navigator.deviceMemory || 'unknown',
            hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
            screenResolution: `${screen.width}x${screen.height}`,
            availableScreenResolution: `${screen.availWidth}x${screen.availHeight}`,
            timezoneOffset: new Date().getTimezoneOffset(),
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            sessionStorage: !!window.sessionStorage,
            localStorage: !!window.localStorage,
            indexedDb: !!window.indexedDB,
            platform: navigator.platform,
            plugins: this.getPlugins(),
            canvas: await this.getCanvasFingerprint(),
            webgl: this.getWebGLFingerprint(),
            fonts: this.getFonts()
        };

        return components;
    }

    getPlugins() {
        const plugins = [];
        for (let i = 0; i < navigator.plugins.length; i++) {
            plugins.push(navigator.plugins[i].name);
        }
        return plugins.sort();
    }

    async getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const text = 'BibleTeacher,🎵';
            
            ctx.textBaseline = 'top';
            ctx.font = '14px "Arial"';
            ctx.textBaseline = 'alphabetic';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText(text, 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText(text, 4, 17);
            
            return canvas.toDataURL();
        } catch (e) {
            return 'unsupported';
        }
    }

    getWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) {
                return 'unsupported';
            }

            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            return {
                vendor: gl.getParameter(gl.VENDOR),
                renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'unknown'
            };
        } catch (e) {
            return 'unsupported';
        }
    }

    getFonts() {
        const baseFonts = ['monospace', 'sans-serif', 'serif'];
        const testFonts = [
            'Arial', 'Verdana', 'Times New Roman', 'Courier New', 'Georgia',
            'Palatino', 'Garamond', 'Bookman', 'Comic Sans MS', 'Trebuchet MS',
            'Impact'
        ];
        
        const testString = 'mmmmmmmmmmlli';
        const testSize = '72px';
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const baseFontWidths = {};
        baseFonts.forEach(baseFont => {
            ctx.font = testSize + ' ' + baseFont;
            baseFontWidths[baseFont] = ctx.measureText(testString).width;
        });
        
        const availableFonts = [];
        testFonts.forEach(testFont => {
            let detected = false;
            baseFonts.forEach(baseFont => {
                ctx.font = testSize + ' ' + testFont + ', ' + baseFont;
                const width = ctx.measureText(testString).width;
                if (width !== baseFontWidths[baseFont]) {
                    detected = true;
                }
            });
            if (detected) {
                availableFonts.push(testFont);
            }
        });
        
        return availableFonts;
    }

    async hashString(str) {
        const encoder = new TextEncoder();
        const data = encoder.encode(str);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    }

    static async get() {
        const stored = localStorage.getItem('browserFingerprint');
        if (stored) {
            return stored;
        }
        
        const fp = new BrowserFingerprint();
        return await fp.generate();
    }
}

window.BrowserFingerprint = BrowserFingerprint;
