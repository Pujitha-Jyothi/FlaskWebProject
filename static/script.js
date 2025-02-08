// script.js
document.querySelectorAll('.sidebar .button').forEach(button => {
    button.addEventListener('click', () => {
        alert('Navigating to ' + button.innerText);
    });
});
