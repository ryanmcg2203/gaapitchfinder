if (location.protocol === "http:") {
  location.replace("https://" + location.host + location.pathname + location.search + location.hash);
}

window.dataLayer = window.dataLayer || [];
function gtag() {
  dataLayer.push(arguments);
}

gtag("js", new Date());
gtag("config", "G-8R6YMPVNWH");
