/**
 * Wild Wasteland easter egg: the Konami code.
 *
 * Only loaded when the current user has wild wasteland mode enabled.
 * Entering ↑ ↑ ↓ ↓ ← → ← → B A anywhere on the page makes the page do a
 * barrel roll and grants the user some (utterly useless) extra lives.
 */
(function () {
    const KONAMI_CODE = [
        'ArrowUp', 'ArrowUp',
        'ArrowDown', 'ArrowDown',
        'ArrowLeft', 'ArrowRight',
        'ArrowLeft', 'ArrowRight',
        'b', 'a',
    ];

    const MESSAGES = [
        'Cheat activated: +30 lives. Lives are not redeemable for coffee.',
        'Cheat activated: all hosts are now up. (Display only.)',
        'Cheat activated: infinite coffee. Wait, coffee is already free.',
        'Cheat activated: DNS is no longer to blame. Just kidding, it always is.',
    ];

    let position = 0;
    let rolling = false;

    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ww-barrel-roll {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .ww-barrel-roll {
                animation: ww-barrel-roll 1.5s ease-in-out 1;
                transform-origin: center center;
            }
            .ww-toast {
                position: fixed;
                left: 50%;
                bottom: 2rem;
                transform: translateX(-50%);
                z-index: 9999;
                padding: 0.75rem 1.25rem;
                border-radius: 0.375rem;
                background: #111827;
                color: #fff;
                font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                font-size: 0.875rem;
                box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.3);
                opacity: 0;
                transition: opacity 300ms ease-in-out;
            }
            .ww-toast.ww-toast-visible {
                opacity: 1;
            }
        `;
        document.head.appendChild(style);
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'ww-toast';
        toast.setAttribute('role', 'status');
        toast.textContent = message;
        document.body.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('ww-toast-visible'));

        setTimeout(() => {
            toast.classList.remove('ww-toast-visible');
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        }, 4000);
    }

    function barrelRoll() {
        if (rolling) {
            return;
        }
        rolling = true;

        const html = document.body;
        html.classList.add('ww-barrel-roll');
        html.addEventListener('animationend', () => {
            html.classList.remove('ww-barrel-roll');
            rolling = false;
        }, { once: true });

        showToast(MESSAGES[Math.floor(Math.random() * MESSAGES.length)]);
    }

    function onKeyDown(event) {
        // Don't hijack typing in form fields; the arrow keys are still fine there.
        const target = event.target;
        const isTyping = target && (
            target.tagName === 'INPUT' ||
            target.tagName === 'TEXTAREA' ||
            target.isContentEditable
        );
        const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;

        if (isTyping && key.length === 1) {
            position = 0;
            return;
        }

        if (key === KONAMI_CODE[position]) {
            position++;
            if (position === KONAMI_CODE.length) {
                position = 0;
                barrelRoll();
            }
        } else {
            // Allow the first key of the sequence to restart matching immediately.
            position = key === KONAMI_CODE[0] ? 1 : 0;
        }
    }

    injectStyles();
    document.addEventListener('keydown', onKeyDown);
})();
