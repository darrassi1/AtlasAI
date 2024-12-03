<script>
  import { agentState } from "$lib/store";
  import { API_BASE_URL, socket } from "$lib/api";

  socket.on('screenshot', function(msg) {
    const data = msg['data'];
    const img = document.querySelector('.browser-img');
    img.src = `data:image/png;base64,${data}`;
  });

</script>

<div class="w-full h-full flex flex-col border-[3px] rounded-xl overflow-y-auto bg-browser-window-background border-window-outline">
  <div class="p-2 flex items-center border-b border-border bg-browser-window-ribbon h-12">
    <div class="flex space-x-2 ml-2 mr-4">

     <!--  <div class="w-3 h-3 bg-red-500 rounded-full animate-blink"></div>
      <div class="w-3 h-3 bg-blue-500 rounded-full animate-blink animation-delay-200"></div>
      <div class="w-3 h-3 bg-green-500 rounded-full animate-blink animation-delay-400"></div>-->
    </div>
    <input
      type="text"
      id="browser-url"
      class="flex-grow h-7 text-xs rounded-lg p-2 overflow-x-auto bg-browser-window-search text-browser-window-foreground"
      placeholder="atlas://newtab"
      value={$agentState?.browser_session.url || ""}
    />
  </div>
  <div id="browser-content" class="flex-grow overflow-y-auto">
    {#if $agentState?.browser_session.screenshot}
      <img
        class="browser-img"
        src={API_BASE_URL + "/api/get-browser-snapshot?snapshot_path=" + $agentState?.browser_session.screenshot}
        alt="Browser snapshot"
      />
    {:else}
      <div class="text-gray-400 text-sm text-center mt-5"><strong>💡 TIP:</strong> You can include a Git URL in your prompt to clone a repo!</div>
    {/if}
  </div>
</div>

<style>
  #browser-url {
    pointer-events: none
  }

@keyframes blink {
  0% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0;
    transform: scale(0.8);
  }

  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-blink {
  animation: blink 1s ease-in-out infinite;
}

  .browser-img {
    display: block;
    object-fit: contain;
  }
</style>