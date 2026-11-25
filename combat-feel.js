// Adventure enemies lose their guard on the first matching blow. The exported
// game still owns pickups, lethal hits, wrong answers, boss forms and scoring.
window.CombatFeel = (() => {
  "use strict";

  const installed = new WeakSet();

  function install(scene, { training, touchMode }) {
    if (installed.has(scene)) return;
    installed.add(scene);

    const broken = new WeakSet();
    const landings = new WeakMap();
    const impactTimes = new WeakMap();
    const ink = scene.add.graphics().setDepth(18);
    const bursts = [];
    let heroHitAt = -Infinity;
    const startArena = scene.startArena;
    const doAttack = scene.doAttack;
    const hurtHero = scene.hurtHero;

    function markHit(x, y, color, facing, caption) {
      bursts.push({ x, y, color, facing, at: scene.now });
      if (!caption) return;
      const note = scene.add.text(x, y - 86, caption, {
        fontFamily: scene.hudFlask.style.fontFamily,
        fontSize: "26px", fontStyle: "bold", color: "#" + color.toString(16),
        stroke: "#241d26", strokeThickness: 6
      }).setOrigin(0.5, 1).setDepth(36);
      scene.tweens.add({
        targets: note, y: note.y - 26, alpha: 0, delay: 290, duration: 310,
        onComplete: () => note.destroy()
      });
    }

    function guardSound() {
      const sound = scene.sound;
      const context = sound.context;
      if (sound.mute || !sound.volume || context?.state !== "running" || !sound.destination) return;
      const at = context.currentTime;
      const tone = context.createOscillator();
      const volume = context.createGain();
      tone.type = "triangle";
      tone.frequency.setValueAtTime(640, at);
      tone.frequency.exponentialRampToValueAtTime(170, at + 0.10);
      volume.gain.setValueAtTime(0.12, at);
      volume.gain.exponentialRampToValueAtTime(0.001, at + 0.12);
      tone.connect(volume);
      volume.connect(sound.destination);
      tone.onended = () => { tone.disconnect(); volume.disconnect(); };
      tone.start(at);
      tone.stop(at + 0.12);
    }

    scene.startArena = function (arena) {
      const result = startArena.call(this, arena);
      if (!training && arena === this.arenas[0]) {
        this.tip("看石台上的释义选武器，砍中一次破防，再砍一次击败词怪", 4700);
      }
      return result;
    };

    scene.doAttack = function (...args) {
      const weapon = this.held;
      const enemy = weapon && this.targetInFront();
      const matched = enemy && weapon.gloss === enemy.word.g;
      if (matched && !training && !this.arena.boss && !broken.has(enemy)) {
        // The base unarmed swing supplies its effects without consuming a weapon
        // or awarding a kill. Restore the same object before returning the frame.
        this.held = null;
        try {
          doAttack.apply(this, args);
        } finally {
          this.held = weapon;
        }
        broken.add(enemy);
        this.forestGuardContactAt = this.now;
        impactTimes.set(enemy, this.now);
        enemy.state = "stun";
        enemy.t = enemy.elite ? 0.47 : 0.60;
        enemy.vx = this.face * (enemy.elite ? 290 : 410);
        enemy.vy = Math.min(enemy.vy, -145);
        enemy.spr.anims.stop();
        enemy.label.setColor("#ffdc83").setText("◇ " + enemy.word.w);
        markHit(enemy.x, enemy.y - 73, 0xffdb80, this.face, "破防 · 再击");
        this.cameras.main.shake(55, 0.0023);
        guardSound();
        return;
      }
      const kills = this.kills;
      const result = doAttack.apply(this, args);
      if (enemy && this.kills > kills) {
        markHit(enemy.x, enemy.y - 78, 0xffedac, this.face);
      }
      return result;
    };

    scene.hurtHero = function (...args) {
      const hp = this.hp;
      const hit = hurtHero.apply(this, args);
      if (hit) {
        heroHitAt = this.now;
        const face = this.body.x >= args[1] ? 1 : -1;
        markHit(this.body.x, this.body.body.bottom - 72, 0xff997c, face,
          "−" + (hp - Math.max(this.hp, 0)) + " ♥");
      }
      return hit;
    };

    function drawDrops(arena) {
      const near = scene.nearWeapon();
      for (const weapon of arena.weapons) {
        // Label the destination during descent. The native bubble is also
        // recreated on a swap, so its translated text always matches the item.
        const selected = weapon === near;
        const bubble = weapon.bubble;
        bubble.setVisible(true).setScale(selected ? 1.03 : (touchMode ? 0.95 : 0.88));
        bubble.setAlpha(selected ? 1 : 0.90);
        const text = bubble.list[1];
        const color = selected ? "#7a390e" : "#14121f";
        if (text.style.color !== color) text.setColor(color);
        if (weapon.landed && !landings.has(weapon)) landings.set(weapon, scene.now);
        const age = landings.has(weapon) ? scene.now - landings.get(weapon) : -1;
        if (age < 0 || age < 0.32 || selected) {
          const radius = age < 0 ? 23 : age < 0.32 ? 22 + 26 * age / 0.32 : 27;
          ink.lineStyle(3, selected ? 0xffdb80 : 0xffefd2, 0.8);
          ink.strokeEllipse(weapon.x, weapon.y + 4, radius * 2, 10);
        }
      }
    }

    function drawBursts() {
      for (let i = bursts.length - 1; i >= 0; i--) {
        const hit = bursts[i];
        const t = (scene.now - hit.at) / 0.18;
        if (t >= 1) {
          bursts.splice(i, 1);
          continue;
        }
        ink.lineStyle(4 * (1 - t) + 1, hit.color, 1 - t);
        for (const angle of [-1.12, -0.55, 0.14, 0.70]) {
          const dx = Math.cos(angle) * hit.facing;
          const dy = Math.sin(angle);
          const reach = 14 + 30 * t;
          ink.lineBetween(hit.x + dx * reach, hit.y + dy * reach,
            hit.x + dx * (reach + 16), hit.y + dy * (reach + 16));
        }
      }
    }

    function render() {
      ink.clear();
      if (scene.arena) {
        drawDrops(scene.arena);
        for (const enemy of scene.arena.enemies) {
          if (!impactTimes.has(enemy)) continue;
          if (scene.now - impactTimes.get(enemy) < 0.09) enemy.spr.setTintFill(0xffe6aa);
          else { enemy.spr.clearTint(); impactTimes.delete(enemy); }
        }
      }
      if (Number.isFinite(heroHitAt)) {
        if (scene.now - heroHitAt < 0.085) scene.heroSpr.setTint(0xffb4a1);
        else { scene.heroSpr.clearTint(); heroHitAt = -Infinity; }
      }
      drawBursts();
    }

    scene.events.on("postupdate", render);
    scene.events.once("shutdown", () => {
      scene.events.off("postupdate", render);
      scene.startArena = startArena;
      scene.doAttack = doAttack;
      scene.hurtHero = hurtHero;
      delete scene.forestGuardContactAt;
      installed.delete(scene);
    });
  }

  return { install };
})();
