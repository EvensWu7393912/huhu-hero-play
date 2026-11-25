// This layer owns the menus. All game controls and physics stay in Phaser.
(() => {
  const url = new URL(location.href);
  const touchMode = navigator.maxTouchPoints > 0 || url.searchParams.has("touch");
  if (touchMode && !url.searchParams.has("touch")) {
    url.searchParams.set("touch", "1");
    try {
      history.replaceState(history.state, "", url);
    } catch {
      // Some WebViews only allow the exported game's native touch detection.
    }
  }

  const get = id => document.getElementById(id);
  const stage = get("stage");
  const menu = get("menu");
  const difficultyNotes = {
    easy: "A1 词汇 · 4 瓶药",
    normal: "A1 至 B1 词汇 · 3 瓶药",
    hard: "A2 至 B1 词汇 · 2 瓶药",
  };
  let difficulty = "normal";
  try {
    const saved = localStorage.getItem("huhu-forest-difficulty");
    if (Object.prototype.hasOwnProperty.call(difficultyNotes, saved)) difficulty = saved;
  } catch {
    // The game is also playable without browser storage.
  }
  let scene;
  let view = "camp";
  let route;
  let wasPortrait = stage.clientHeight > stage.clientWidth;

  function selectDifficulty(value) {
    difficulty = value;
    for (const input of document.querySelectorAll("input[name=difficulty]")) {
      input.checked = input.value === value;
      input.parentElement.classList.toggle("selected", input.checked);
    }
    get("difficulty-note").textContent = difficultyNotes[value];
  }
  selectDifficulty(difficulty);
  get("difficulty").addEventListener("change", event => {
    selectDifficulty(event.target.value);
    try { localStorage.setItem("huhu-forest-difficulty", difficulty); } catch {}
  });

  function stopScene() {
    if (!scene?.sys.isActive()) return;
    scene.sys.pause();
    scene.input.resetPointers();
    for (const action of Object.keys(scene.touch)) scene.touch[action] = false;
  }

  function dialog(nextView, title, detail, primary, secondary = "") {
    stopScene();
    view = nextView;
    menu.dataset.view = view;
    menu.hidden = false;
    get("camp").hidden = true;
    get("pause").hidden = true;
    get("dialog").hidden = false;
    get("dialog-title").textContent = title;
    get("detail").textContent = detail;
    get("primary").textContent = primary;
    get("secondary").hidden = !secondary;
    get("secondary").textContent = secondary;
    if (!touchMode) get("primary").focus();
  }

  function resume() {
    if (document.hidden || !scene) return;
    view = "playing";
    menu.hidden = true;
    get("pause").hidden = false;
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    scene.sys.resume();
  }

  function pause() {
    if (view !== "playing") return;
    const controls = touchMode
      ? "左右键移动，点「跳」可二段跳，「砍」可捡起武器或攻击。"
      : "A / D 移动，空格跳跃，J 捡武器或攻击，K 翻滚，Q 喝药。";
    dialog("paused", route === "training" ? "练习已暂停" : "冒险已暂停", controls, "继续", "返回营地");
  }

  function enter(nextRoute) {
    if (view !== "camp" || !scene || document.hidden) return;
    route = nextRoute;
    if (route === "training") {
      window.ForestTutorial.start(scene, {
        touchMode,
        onComplete() {
          dialog("trained", "练习完成", "你已经用释义匹配的武器击败了词怪。回营地选好难度，就能穿过林间石门去冒险。", "回营地选难度");
        },
      });
    } else {
      window.ForestProgression.install(scene, difficulty);
      window.ForestTrail.install(scene);
    }
    resume();
  }

  get("training").addEventListener("click", () => enter("training"));
  get("adventure").addEventListener("click", () => enter("adventure"));
  get("pause").addEventListener("click", pause);
  get("primary").addEventListener("click", () => {
    if (view === "paused" || view === "leaving") resume();
    else location.reload();
  });
  get("secondary").addEventListener("click", () => {
    if (view === "leaving") {
      location.reload();
    } else if (view === "paused") {
      dialog("leaving", "结束本次试玩？", "返回营地会结束本局，下次从起点出发。", "继续游玩", "结束并返回");
    }
  });
  // Let native radio buttons and focused menu buttons handle their own keys.
  menu.addEventListener("keydown", event => {
    event.stopPropagation();
    if (event.key === "Escape" && (view === "paused" || view === "leaving")) resume();
  });
  window.addEventListener("keydown", event => {
    if (event.key === "Escape" && !event.repeat) {
      if (view === "playing") pause();
      else if (view === "paused" || view === "leaving") resume();
    }
  });

  document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
  window.addEventListener("pagehide", pause);
  window.addEventListener("blur", pause);
  function resize() {
    const scale = window.__game?.scale;
    if (scale?.canvas && stage.clientWidth && stage.clientHeight) {
      scale.setParentSize(stage.clientWidth, stage.clientHeight);
    }
    const portrait = stage.clientHeight > stage.clientWidth;
    if (touchMode && portrait && !wasPortrait) pause();
    wasPortrait = portrait;
  }
  if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
  window.addEventListener("resize", resize);

  document.addEventListener("DOMContentLoaded", () => {
    const game = window.__game;
    if (!game || !window.ForestTutorial || !window.ForestProgression || !window.ForestTrail) {
      dialog("error", "游戏加载失败", "请检查试玩包是否解压完整，或重新打开页面。", "重新加载");
      return;
    }
    function onSceneReady() {
      if (!window.__scene) return;
      scene = window.__scene;
      game.events.off("poststep", onSceneReady);
      stopScene();
      resize();
      get("status").hidden = true;
      get("training").disabled = false;
      get("adventure").disabled = false;
    }
    game.events.on("poststep", onSceneReady);
    onSceneReady();
  });
})();
