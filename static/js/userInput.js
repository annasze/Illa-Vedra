function getUserInput(paramName) {
    const urlParams = new URLSearchParams(window.location.search);
    return {
        userInput: urlParams.get(paramName)
    }
}