mergeInto(LibraryManager.library, {
    pokerRaceNotify: function(type, data) {
        if (typeof window !== 'undefined' && window.parent !== window) {
            var payload = {
                type: Pointer_stringify(type),
                source: 'poker-race'
            };
            if (data !== 0) {
                payload.data = Pointer_stringify(data);
            }
            window.parent.postMessage(payload, '*');
        }
    },
    pokerRaceOnGameOver: function() {
        Module.pokerRaceNotify('gameover', 0);
    },
    pokerRaceOnRoundEnd: function() {
        Module.pokerRaceNotify('round-end', 0);
    },
    pokerRaceOnPlayerTurn: function(playerIndex) {
        Module.pokerRaceNotify('player-turn', 0);
    }
});

var PokerRaceAPI = {
    pause: function() {
        if (typeof Module !== 'undefined' && Module.pauseGame) {
            Module.pauseGame();
        }
    },
    resume: function() {
        if (typeof Module !== 'undefined' && Module.resumeGame) {
            Module.resumeGame();
        }
    },
    setVolume: function(master, music, sfx) {
        if (typeof Module !== 'undefined' && Module.setVolume) {
            Module.setVolume(master, music, sfx);
        }
    },
    startGame: function() {
        if (typeof Module !== 'undefined' && Module.startGame) {
            Module.startGame();
        }
    },
    restartGame: function() {
        if (typeof Module !== 'undefined' && Module.restartGame) {
            Module.restartGame();
        }
    },
    getGameState: function() {
        if (typeof Module !== 'undefined' && Module.getGameState) {
            return Module.getGameState();
        }
        return -1;
    }
};

if (typeof window !== 'undefined') {
    window.PokerRaceAPI = PokerRaceAPI;

    window.addEventListener('message', function(event) {
        if (typeof Module === 'undefined') return;
        if (!event.data || event.data.source === 'poker-race') return;

        var type = event.data.type;
        var data = event.data.data;

        switch (type) {
            case 'pause':
                if (Module.pauseGame) Module.pauseGame();
                break;
            case 'resume':
                if (Module.resumeGame) Module.resumeGame();
                break;
            case 'setVolume':
                if (Module.setVolume && data) {
                    Module.setVolume(data.master || 1, data.music || 1, data.sfx || 1);
                }
                break;
            case 'start':
                if (Module.startGame) Module.startGame();
                break;
            case 'restart':
                if (Module.restartGame) Module.restartGame();
                break;
        }
    });

    window.addEventListener('load', function() {
        if (window.parent !== window) {
            window.parent.postMessage({ type: 'ready', source: 'poker-race' }, '*');
        }
    });
}