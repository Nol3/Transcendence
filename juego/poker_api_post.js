mergeInto(LibraryManager.library, {
    pokerRaceNotify: function(type, data) {
        if (typeof window !== 'undefined' && window.parent !== window) {
            try {
                var typeStr = (typeof type === 'number') ? Pointer_stringify(type) : type;
                var payload = { type: typeStr, source: 'poker-race' };
                if (data !== 0) {
                    payload.data = (typeof data === 'number') ? Pointer_stringify(data) : data;
                }
                window.parent.postMessage(payload, '*');
            } catch (e) {}
        }
    },
    pokerRaceNotifyInt: function(type, value) {
        if (typeof window !== 'undefined' && window.parent !== window) {
            try {
                var typeStr = (typeof type === 'number') ? Pointer_stringify(type) : type;
                window.parent.postMessage({ type: typeStr, value: value, source: 'poker-race' }, '*');
            } catch (e) {}
        }
    }
});

var PokerRaceAPI = {
    pause: function() { if (Module && Module._gamePause) Module._gamePause(1); },
    resume: function() { if (Module && Module._gamePause) Module._gamePause(0); },
    setVolume: function(master, music, sfx) {
        if (Module && Module._gameSetVolume) Module._gameSetVolume(master, music, sfx);
    },
    restart: function() { if (Module && Module._gameRestart) Module._gameRestart(); },
    getState: function() { if (Module && Module._gameGetState) return Module._gameGetState(); return -1; }
};

var PokerRaceGame = {
    onGameOver: function(score, winnerName) {
        window.parent.postMessage({
            type: 'gameover',
            score: score,
            winner: winnerName,
            source: 'poker-race'
        }, '*');
    },
    onRoundEnd: function(round) {
        window.parent.postMessage({
            type: 'round-end',
            round: round,
            source: 'poker-race'
        }, '*');
    },
    onPlayerTurn: function(playerName, playerIndex) {
        window.parent.postMessage({
            type: 'player-turn',
            player: playerName,
            index: playerIndex,
            source: 'poker-race'
        }, '*');
    }
};

if (typeof window !== 'undefined') {
    window.PokerRaceAPI = PokerRaceAPI;
    window.PokerRaceGame = PokerRaceGame;

    window.addEventListener('message', function(event) {
        if (event.data && event.data.source === 'poker-race') return;
        if (!event.data || !event.data.type) return;

        var type = event.data.type;
        var data = event.data;

        switch (type) {
            case 'pause':
                if (Module && Module._gamePause) Module._gamePause(1);
                break;
            case 'resume':
                if (Module && Module._gamePause) Module._gamePause(0);
                break;
            case 'setVolume':
                if (Module && Module._gameSetVolume) {
                    Module._gameSetVolume(data.master || 1, data.music || 1, data.sfx || 1);
                }
                break;
            case 'restart':
                if (Module && Module._gameRestart) Module._gameRestart();
                break;
        }
    });

    if (window.parent !== window) {
        window.parent.postMessage({ type: 'poker-race-ready', source: 'poker-race' }, '*');
    }
}