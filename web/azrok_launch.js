(() => {
  const button = document.getElementById("connect-button");
  const row = document.getElementById("preservation-server");
  const status = document.getElementById("launch-status");
  const onlineCount = document.getElementById("online-count");
  const browserKey = "azrok.private-browser-id.v1";
  const appStem = "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4_questfont1";
  const rootStem = "TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2";
  const runtimeStem = "boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1r10cwdrepublish1";
  const jitCacheUrl = "/profiles/azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1r10cwdrepublish1-map13009736-r1-20260901.zip";
  const runtimeIdentityFlags = ["faceWisHle", "ownerThreadIdentity", "faceOwnerTrace", "faceOwnerReadwait", "faceOwnerCausalWis", "faceRetry", "faceScopedGen", "faceWarmup", "faceCwdDiscovery", "faceCwdSafe"];
  // The game page owns archive loading and displays its boot progress. Do not
  // hold an admitted session here waiting for speculative downloads/cache writes.

  const browserId = () => {
    const existing = localStorage.getItem(browserKey);
    if (/^[A-Za-z0-9_-]{22,128}$/.test(existing || "")) return existing;
    const random = crypto.randomUUID
      ? crypto.randomUUID()
      : Array.from(crypto.getRandomValues(new Uint8Array(18)), byte => byte.toString(16).padStart(2, "0")).join("");
    const id = "browser_" + random;
    localStorage.setItem(browserKey, id);
    return id;
  };

  const failureMessage = code => ({
    400: "이 브라우저의 사설 연결 식별자를 만들지 못했습니다. 페이지 데이터를 지운 뒤 다시 시도해 주세요.",
    403: "이 주소는 사설 LAN 또는 Tailscale에서만 접속할 수 있습니다.",
    409: "보존 계정을 준비하지 못했습니다. 서버 관제 화면에서 계정 상태를 확인해 주세요.",
    503: "보존 계정 서비스가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요."
  })[code] || "아즈로크 서버에 접속하지 못했습니다. 잠시 후 다시 시도해 주세요.";

  const trustedBridgeUrl = () => {
    const host = location.hostname.toLowerCase();
    if (host === "playazrok.com") {
      return "wss://playazrok.com/azrok-ws";
    }
    if (host === "<tailscale-ip>" || host === "<tailnet-host>") {
      return "wss://<tailnet-host>/azrok-ws";
    }
    return "";
  };

  const connect = async () => {
    button.disabled = true;
    status.classList.remove("error");
    status.textContent = "보존 계정과 광장 서버 접속 정보를 확인하고 있습니다...";
    try {
      const response = await fetch("/api/private-session", {
        cache: "no-store",
        credentials: "same-origin",
        headers: {"X-Azrok-Browser-Id": browserId()}
      });
      const admission = await response.json().catch(() => null);
      if (!response.ok) throw new Error(failureMessage(response.status));
      if (!admission ||
          !/^[A-Za-z0-9_.-]{20,320}$/.test(admission.instance || "") ||
          !/^run_azrok_(seh|peer111|multi2|player3|player4|player5|player6|account)\.bat$/.test(admission.launcher || "") ||
          !/^[A-Za-z0-9_]{3,13}$/.test(admission.account || "")) {
        throw new Error("서버가 올바르지 않은 접속 정보를 보냈습니다. 잠시 후 다시 시도해 주세요.");
      }
      status.textContent = "접속 허가 완료. 원본 아즈로크 클라이언트를 실행합니다...";
      const target = new URL("index_d3d9web_pathouse.html", location.href);
      target.searchParams.set("instance", admission.instance);
      target.searchParams.set("p", admission.launcher);
      target.searchParams.set("args", admission.account);
      target.searchParams.set("app", appStem);
      target.searchParams.set("root", rootStem);
      target.searchParams.set("runtimeStem", runtimeStem);
      target.searchParams.set("jitCacheUrl", jitCacheUrl);
      for (const flag of runtimeIdentityFlags) target.searchParams.set(flag, "1");
      target.searchParams.set("autorun", "1");
      const trustedBridge = trustedBridgeUrl();
      if (trustedBridge) target.searchParams.set("ws", trustedBridge);
      location.assign(target.href);
    } catch (error) {
      status.textContent = String(error?.message || failureMessage(0));
      status.classList.add("error");
      button.disabled = false;
    }
  };

  const refreshOnlineCount = async () => {
    if (!onlineCount) return;
    try {
      const response = await fetch("/api/private-server-status", {
        cache: "no-store",
        credentials: "same-origin"
      });
      const result = await response.json().catch(() => null);
      if (!response.ok || !Number.isInteger(result?.online) || result.online < 0) {
        throw new Error("invalid server status");
      }
      onlineCount.textContent = `· 현재 ${result.online}명 접속`;
    } catch (_error) {
      onlineCount.textContent = "· 접속 인원 확인 불가";
    }
  };

  row.addEventListener("dblclick", connect);
  button.addEventListener("click", connect);
  refreshOnlineCount();
  setInterval(refreshOnlineCount, 10000);
})();
