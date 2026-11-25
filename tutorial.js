// This lesson runs in a fresh copy of the game scene. The shell starts another
// fresh scene for the adventure so practice never changes its combat statistics.
window.ForestTutorial = (() => {
  const practiceWord = { w: "duck", g: "鸭子", d: "鸽子", l: "A1" };

  function start(scene, { touchMode, onComplete }) {
    const arena = scene.arenas[0];
    const initialKills = scene.kills;
    const originalDamage = scene.hurtHero;
    const startX = arena.L + 120;
    const go = touchMode ? "按住 ▶" : "按住 D 或 →";
    const jump = touchMode ? "点「跳」" : "按空格";
    const airRoll = touchMode ? "点「滚」空翻" : "按 K 空翻";
    const attack = touchMode ? "点「砍」" : "按 J";
    let step = "move";
    let lastMistakes = scene.mistakes;
    let retry = false;
    let stopped = false;

    // Start inside the original bounded arena. Spawn the practice encounter
    // only after the player has moved and jumped, keeping the steps actionable.
    scene.body.body.reset(startX, 568);
    scene.face = 1;
    arena.spec = [];
    arena.spots = [
      { x: arena.L + 410, y: 624 },
      { x: arena.L + 690, y: 624 }
    ];
    scene.startArena(arena);
    scene.hurtHero = () => false;
    scene.hudTip.setVisible(false);

    // Leave the top-center slot free for the original held-weapon caption.
    const hud = scene.add.text(640, 88, "", {
      fontFamily: 'system-ui, "PingFang SC", sans-serif',
      fontSize: "31px",
      fontStyle: "bold",
      color: "#fff3d5",
      backgroundColor: "#25372f",
      align: "center",
      padding: { x: 18, y: 7 },
      lineSpacing: 2
    }).setOrigin(0.5, 0).setScrollFactor(0).setDepth(160);

    function instruct(heading, message) {
      const prompt = heading + "\n" + message;
      if (hud.text !== prompt) hud.setText(prompt);
    }

    function spawnEncounter() {
      const enemy = scene.spawnEnemy(arena, practiceWord, false, arena.R - 170);
      // It waits at the far end while the player reads the two weapon glosses.
      enemy.t = Infinity;
      arena.enemies.push(enemy);
      scene.dropWeapons(arena);
      step = "pick";
    }

    function onJump() {
      if (step === "jump") spawnEncounter();
    }

    function stop() {
      if (stopped) return;
      stopped = true;
      scene.events.off("postupdate", update);
      scene.events.off("hero-jump", onJump);
      scene.events.off("shutdown", stop);
      scene.hurtHero = originalDamage;
      scene.hudTip.setVisible(true);
      hud.destroy();
    }

    function update() {
      if (step === "move" && scene.body.x >= startX + 90) {
        step = "jump";
      }
      if (scene.kills > initialKills && step !== "done") {
        step = "done";
        instruct("击中词怪！", "duck 是「鸭子」。准备出发！");
        scene.time.delayedCall(1100, () => {
          if (stopped) return;
          stop();
          onComplete();
        });
      }
      if (step === "done") return;
      if (step === "move") {
        instruct("移动", go + "，向右走几步");
      } else if (step === "jump") {
        instruct("跳跃", jump + "起跳，可再跳一次，也可" + airRoll);
      } else if (scene.held) {
        step = "strike";
        instruct("斩杀", "走向 duck，面朝它，靠近后" + attack);
      } else {
        if (scene.mistakes > lastMistakes) {
          retry = true;
          lastMistakes = scene.mistakes;
        }
        step = "pick";
        const weapon = scene.nearWeapon();
        if (weapon) {
          instruct("拾取", "这把写着「" + weapon.gloss + "」。" + attack + "拾取");
        } else {
          const target = arena.weapons.find(w => w.gloss === practiceWord.g);
          const side = target && scene.body.x > target.x ? "左" : "右";
          const message = retry
            ? "duck 是「鸭子」。往" + side + "走，重新选一把"
            : "往" + side + "走到地上的武器旁，找出 duck 对应的中文";
          instruct(retry ? "再试一次" : "拾取", message);
        }
      }
    }

    scene.events.on("postupdate", update);
    scene.events.on("hero-jump", onJump);
    scene.events.once("shutdown", stop);
    update();
    return { stop };
  }

  return { start };
})();
