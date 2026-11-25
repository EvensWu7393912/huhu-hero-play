// All positions are in the exported 158 × 162 hero frame. Weapon angles are
// measured clockwise from an upright blade in a right-facing pose.
(() => {
  "use strict";

  const mounted = new WeakSet();

  // The sword is painted point-down. The other three are painted head-up.
  // Pivot about the wrapping on each handle, including the off-centre spear.
  const grips = {
    sword:  { x: 18, y: 21, turn: 180, scale: 1.02, ready: 53, back: -64, hit: 84, end: 106 },
    axe:    { x: 12, y: 81, turn:   0, scale: 0.98, ready: 54, back: -73, hit: 80, end: 97 },
    hammer: { x: 23, y: 82, turn:   0, scale: 0.98, ready: 51, back: -88, hit: 81, end: 95 },
    spear:  { x:  6, y: 89, turn:   0, scale: 1.16, ready: 51, back:  79, hit:  89, end:  76 }
  };

  const hands = [
    [71, 117], [121, 91], [109, 92], [119, 99],
    [104, 102], [144, 74], null, [97, 78],
    [94, 106], [64, 58], [126, 122], [146, 89]
  ];

  function mix(start, end, t) {
    return start + (end - start) * Math.min(1, Math.max(0, t));
  }

  function drawWeapon(scene, handCover, key, face, angle) {
    const hero = scene.heroSpr;
    const frame = Number(hero.frame.name);
    // The spear is drawn back in the forward fist at shoulder height.
    // Raised behind the head, the other fist winds up the three swung weapons.
    const slot = key === "spear" && frame === 9 ? [116, 90] : hands[frame];
    const grip = grips[key];
    const sprite = scene.heldSpr;
    if (!slot || !grip) {
      sprite.setVisible(false);
      return;
    }

    // A signed scale mirrors the entire weapon around the off-centre grip.
    // Paint the handle in front of the sleeve and restore the knuckles on top.
    sprite.setVisible(true).setTexture(key).setDepth(hero.depth + 0.1)
      .setOrigin(grip.x / sprite.width, grip.y / sprite.height)
      .setPosition(
        hero.x + face * (slot[0] - hero.displayOriginX) * hero.scaleX,
        hero.y + (slot[1] - hero.displayOriginY) * hero.scaleY
      )
      .setFlip(false, false).setScale(face * grip.scale, grip.scale)
      .setAngle(face * (angle + grip.turn)).setAlpha(hero.alpha);
    handCover.setVisible(true).setFrame(hero.frame.name)
      .setOrigin(hero.originX, hero.originY).setPosition(hero.x, hero.y)
      .setScale(face * hero.scaleX, hero.scaleY).setAlpha(hero.alpha)
      .setCrop(slot[0] - 5, slot[1] - 5, 10, 10);
  }

  function install(scene) {
    if (mounted.has(scene)) return;
    mounted.add(scene);

    const handCover = scene.add.image(0, 0, "hero", 0)
      .setDepth(scene.heroSpr.depth + 0.2).setVisible(false);
    const attack = scene.doAttack;
    const draw = scene.drawHero;
    let swing = null;

    scene.doAttack = function (...args) {
      // Damage and a weapon's consumption both resolve inside this call.
      // Remember the equipped art before the original game updates the hand.
      const key = this.held?.key;
      const kills = this.kills;
      const mistakes = this.mistakes;
      const result = attack.apply(this, args);
      this.slashSpr.setVisible(false);
      swing = key && grips[key] ? {
        key, face: this.face, time: this.now,
        hit: this.kills > kills || this.mistakes > mistakes || this.forestGuardContactAt === this.now,
        recoil: this.mistakes > mistakes
      } : null;
      return result;
    };

    scene.drawHero = function (...args) {
      const result = draw.apply(this, args);
      const hero = this.heroSpr;
      const trail = this.slashSpr;
      handCover.setVisible(false);
      trail.setVisible(false);

      const elapsed = swing ? this.now - swing.time : 0;
      if (swing && (elapsed >= (swing.recoil ? 0.17 : 0.30)
          || (this.state !== "attack" && !(this.state === "hurt" && swing.recoil)))) {
        swing = null;
      }

      if (swing) {
        const { key, face, hit, recoil } = swing;
        const grip = grips[key];
        const thrust = key === "spear";
        // Contacts have already resolved at the key press. Show that contact
        // immediately; on a free swing there is time to draw the full wind-up.
        const contactStart = hit ? 0 : 0.073;
        const contactEnd = recoil ? 0.067 : 0.165;
        let frame, angle;
        if (elapsed < contactStart) {
          frame = 9;
          angle = mix(grip.ready, grip.back, elapsed / contactStart);
        } else if (elapsed < contactEnd) {
          frame = thrust ? 11 : 5;
          const t = (elapsed - contactStart) / (contactEnd - contactStart);
          angle = hit ? mix(grip.hit, grip.end, t * 0.30)
            : mix(grip.back, grip.hit, 1 - Math.pow(1 - t, 3));
          if (!thrust) {
            trail.setVisible(true).setPosition(hero.x + face * 91, hero.y - 82)
              .setFlipX(face > 0).setAlpha((0.80 - 0.40 * t) * hero.alpha);
          }
        } else {
          frame = 10;
          const duration = (recoil ? 0.17 : 0.30) - contactEnd;
          const start = hit ? mix(grip.hit, grip.end, 0.30) : grip.hit;
          const end = recoil ? grip.back * 0.5 : grip.end;
          angle = mix(start, end, (elapsed - contactEnd) / duration);
        }

        hero.anims.stop();
        hero.setFrame(frame).setFlipX(face < 0);
        drawWeapon(this, handCover, key, face, angle);
      } else if (this.held && this.state === "normal") {
        const key = this.held.key;
        if (grips[key]) {
          if (Number(hero.frame.name) === 0) hero.setFrame(8);
          drawWeapon(this, handCover, key, this.face, grips[key].ready);
        }
      } else {
        this.heldSpr.setVisible(false);
      }
      return result;
    };

    function hideWeapons() {
      handCover.setVisible(false);
      scene.heldSpr.setVisible(false);
      scene.slashSpr.setVisible(false);
    }
    // Scene time freezes on pause; the next draw resumes the same pose.
    scene.events.on("pause", hideWeapons);
    scene.events.once("shutdown", () => {
      scene.events.off("pause", hideWeapons);
      scene.doAttack = attack;
      scene.drawHero = draw;
      swing = null;
      mounted.delete(scene);
    });
  }

  window.WeaponMotion = { install };
})();
