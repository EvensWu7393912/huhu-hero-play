// The forest seal uses the first encounter's vocabulary and the scene's own
// one-way platforms. Its open state lasts for the current adventure.
(() => {
  const installed = new WeakSet();

  function install(scene) {
    if (installed.has(scene)) return;

    const word = scene.arenas[0].spec[0].word;
    const firstPlatformX = 520;
    const secondPlatformX = 765;
    const platformY = 480;
    const gateX = 944;
    const correctFirst = Math.random() < 0.5;
    let open = false;
    let lastLanding = null;
    let retryUntil = 0;

    // The first platform already exists in the exported level.
    scene.addPlatform("platform2", secondPlatformX, platformY);
    const barrier = scene.add.rectangle(gateX, 168, 32, 1160).setVisible(false);
    scene.physics.add.existing(barrier, true);
    scene.walls.add(barrier);

    const flame = scene.add.sprite(gateX, 629, "fire0").setOrigin(0.5, 1)
      .setTint(0x394051).setDepth(8);
    const seal = scene.add.graphics().setDepth(7);
    seal.fillStyle(0xefb46b, 0.16).fillRect(gateX - 9, 0, 18, 610);
    seal.lineStyle(3, 0xffcb82, 0.82).lineBetween(gateX, 0, gateX, 563);
    for (let y = 38; y < 550; y += 84) {
      seal.lineStyle(2, 0xffcb82, 0.86);
      seal.strokePoints([
        { x: gateX, y: y - 11 }, { x: gateX + 7, y },
        { x: gateX, y: y + 11 }, { x: gateX - 7, y }
      ], true);
    }

    function label(x, y, value, size, color) {
      return scene.add.text(x, y, value, {
        fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif',
        fontSize: size + "px", fontStyle: "bold", color, align: "center",
        stroke: "#1c1b2b", strokeThickness: 6
      }).setOrigin(0.5).setDepth(19);
    }
    const title = label(640, 150, "林间石门", 24, "#f0c68f");
    const question = label(640, 199, word.w, 47, "#ffffff");
    const hint = label(640, 249, "跳到意思相符的石台上，点燃门火", 26, "#fff0d5");

    const choices = [firstPlatformX, secondPlatformX].map((x, i) => {
      const correct = (i === 0) === correctFirst;
      const caption = label(x, platformY + 23, correct ? word.g : word.d, 29, "#fff0d5");
      if (caption.width > 213) caption.setScale(213 / caption.width);
      return { x, correct, caption };
    });

    function update() {
      if (open || scene.state === "dead" || scene.state === "win") return;
      if (retryUntil && scene.now >= retryUntil) {
        hint.setText("跳到意思相符的石台上，点燃门火").setColor("#fff0d5");
        retryUntil = 0;
      }
      const body = scene.body.body;
      const landing = scene.onFloor && Math.abs(body.bottom - platformY) < 2
        ? choices.find(choice => Math.abs(body.center.x - choice.x) <= 88)
        : null;
      if (landing === lastLanding) return;
      lastLanding = landing;
      if (!landing) return;

      if (!landing.correct) {
        hint.setText("另一座石台才是「" + word.w + "」的意思").setColor("#ffc18b");
        retryUntil = scene.now + 3;
        return;
      }

      open = true;
      scene.walls.remove(barrier, true, true);
      seal.destroy();
      flame.clearTint().play("fire");
      landing.caption.setColor("#b3efbb");
      title.setText("石门已开");
      question.setText(word.w + "  ·  " + word.g).setFontSize(36);
      hint.setText("向右去林地迎战  →").setColor("#b3efbb");
      scene.ring(gateX);
    }

    installed.add(scene);
    scene.events.on("postupdate", update);
    scene.events.once("shutdown", () => {
      scene.events.off("postupdate", update);
      installed.delete(scene);
    });
  }

  window.ForestTrail = { install };
})();
