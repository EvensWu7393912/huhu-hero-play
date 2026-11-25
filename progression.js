// Difficulty and upgrades for a fresh run of the exported forest scene.
(() => {
  "use strict";

  const difficulties = {
    easy: { name: "轻松", flasks: 4 },
    normal: { name: "标准", flasks: 3 },
    hard: { name: "挑战", flasks: 2 }
  };
  const installed = new WeakSet();
  const regenPerLevel = 6;
  const maxHearts = 5;

  function setVocabulary(scene, difficulty) {
    // Standard keeps the original draw. In Challenge, each A1 slot becomes
    // A2 and each A2/B1 slot becomes B1, including all three boss forms.
    if (difficulty === "normal") return;
    const used = new Set();
    for (const arena of scene.arenas) {
      for (const slot of arena.spec) {
        const level = difficulty === "easy" ? "A1" : (slot.word.l === "A1" ? "A2" : "B1");
        [slot.word] = scene.pickWords(level, 1, used);
      }
    }
  }

  function install(scene, difficulty) {
    if (installed.has(scene)) return;
    const settings = difficulties[difficulty];
    if (!settings) throw new RangeError("Unknown forest difficulty: " + difficulty);
    setVocabulary(scene, difficulty);
    installed.add(scene);

    // These same arena instances are replayed after a death. Keep a per-run
    // ledger even when the game's respawn resets their cleared flags.
    const rewarded = new Set();
    const level = () => rewarded.size + 1;
    const badge = scene.add.text(24, 153, "", {
      fontFamily: scene.hudFlask.style.fontFamily,
      fontSize: "25px",
      fontStyle: "bold",
      color: "#ffe5a2"
    }).setName("forest-level").setScrollFactor(0).setDepth(100).setStroke("#14121f", 6);

    function updateBadge() {
      badge.setText(settings.name + " · Lv." + level());
    }
    updateBadge();
    scene.flasks = settings.flasks;

    const updateBonfires = scene.updateBonfires.bind(scene);
    scene.updateBonfires = () => {
      const before = scene.checkpoint;
      updateBonfires();
      if (scene.checkpoint !== before) scene.flasks = settings.flasks;
    };

    const respawn = scene.respawn.bind(scene);
    scene.respawn = () => {
      respawn();
      scene.flasks = settings.flasks;
    };

    // Award the extra regeneration in the same window as the base game's
    // 42 stamina/s. Rolling and attacking still trigger its recovery delay.
    const updateHero = scene.updateHero.bind(scene);
    scene.updateHero = (dt, input, presses) => {
      if (scene.staminaWait <= 0 && scene.state !== "dead") {
        scene.stamina = Math.min(100, scene.stamina + rewarded.size * regenPerLevel * dt);
      }
      updateHero(dt, input, presses);
    };

    const endArena = scene.endArena.bind(scene);
    scene.endArena = (arena, cleared) => {
      const firstClear = cleared && scene.arena === arena && arena.active
        && scene.state !== "dead" && !rewarded.has(arena);
      endArena(arena, cleared);
      if (!firstClear) return;
      rewarded.add(arena);
      updateBadge();
      const healed = scene.hp < maxHearts;
      scene.hp = Math.min(maxHearts, scene.hp + 1);
      if (!arena.boss) {
        const bonus = "耐力恢复 +" + rewarded.size * regenPerLevel + "/秒";
        scene.tip("升到 Lv." + level() + "　" + bonus + (healed ? "　回复 1 颗心" : ""), 3200);
      }
    };

    const win = scene.win.bind(scene);
    scene.win = () => {
      win();
      scene.subBanner.setText(settings.name + " · Lv." + level() + "\n"
        + "斩杀 " + scene.kills + "　砍错 " + scene.mistakes + " 次　死亡 " + scene.deaths + " 次"
        + "\n\n按 R 或点一下屏幕再来一遍");
    };
  }

  window.ForestProgression = { install };
})();
