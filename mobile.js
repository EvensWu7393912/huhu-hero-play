// The exported scene already owns the combat controls. This shell manages
// the space available to its canvas and pauses that scene during interruptions.
(() => {
  const url = new URL(location.href);
  const touchMode = navigator.maxTouchPoints > 0 || url.searchParams.has("touch");
  if (touchMode && !url.searchParams.has("touch")) {
    // The original build uses this flag for touch devices reporting a desktop UA.
    url.searchParams.set("touch", "1");
    try {
      history.replaceState(history.state, "", url);
    } catch {
      // An embedded frame may forbid URL changes. Keep native phone detection.
    }
  }

  const stage = document.querySelector("#stage");
  const menu = document.querySelector("#menu");
  const title = document.querySelector("#menu-title");
  const rotate = document.querySelector("#rotate");
  const play = document.querySelector("#play");
  const pause = document.querySelector("#pause");
  let scene;
  let started = false;
  let loadFailed = false;
  let wasPortrait = portrait();

  function portrait() {
    return stage.clientHeight > stage.clientWidth;
  }

  function showMenu() {
    if (!touchMode || loadFailed) return;
    if (scene && scene.sys.isActive()) {
      scene.sys.pause();
      scene.input.resetPointers();
      for (const action of Object.keys(scene.touch)) scene.touch[action] = false;
    }
    menu.hidden = false;
    pause.hidden = true;
    title.textContent = started ? "已暂停" : "狐狐勇者";
    rotate.hidden = !portrait();
    play.disabled = !scene;
    if (!scene) play.textContent = "正在加载…";
    else if (portrait()) play.textContent = started ? "竖屏继续" : "竖屏试玩";
    else play.textContent = started ? "继续游戏" : "开始试玩";
  }

  function resize() {
    const scale = window.__game?.scale;
    if (scale?.canvas && stage.clientWidth && stage.clientHeight) {
      scale.setParentSize(stage.clientWidth, stage.clientHeight);
    }
    const isPortrait = portrait();
    if (!menu.hidden || (isPortrait && !wasPortrait)) showMenu();
    wasPortrait = isPortrait;
  }

  play.addEventListener("click", () => {
    if (!scene || document.hidden) return;
    started = true;
    menu.hidden = true;
    pause.hidden = false;
    scene.sys.resume();
  });
  pause.addEventListener("click", showMenu);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) showMenu();
  });
  window.addEventListener("pagehide", showMenu);
  window.addEventListener("blur", showMenu);

  // Phaser may keep the portrait display size after a WebView rotates.
  // Observe the safe-area container, including changes caused by browser chrome.
  if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
  window.addEventListener("resize", resize);

  showMenu();
  document.addEventListener("DOMContentLoaded", () => {
    const game = window.__game;
    if (!game) {
      loadFailed = true;
      menu.hidden = false;
      title.textContent = "游戏加载失败";
      document.querySelector("#instructions").textContent = "请重新打开试玩页面。";
      document.querySelector("#controls").hidden = true;
      rotate.hidden = true;
      play.hidden = true;
      return;
    }
    function onSceneReady() {
      if (!window.__scene) return;
      scene = window.__scene;
      game.events.off("poststep", onSceneReady);
      if (touchMode && game.device.os.desktop) {
        scene.tip("往右走。怪头上是单词，武器里藏着释义", 9000);
      }
      resize();
    }
    game.events.on("poststep", onSceneReady);
    onSceneReady();
  });
})();
