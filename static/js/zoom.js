function onZoom(e, img) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    img.style.transformOrigin = `${x}px ${y}px`;
    img.style.transform = "scale(2.5)";
    document.body.style.cursor = "zoom-in";
};

function offZoom(e, img) {
    img.style.transformOrigin = "center";
    img.style.transform = "scale(1)";
    document.body.style.cursor = "auto";
};
