const countdown = document.querySelector('.countdown');
const containerInput = document.querySelector('.container input');

const startSeconds = Math.floor(Math.random() * (60 - 40 + 1)) + 40;
let count = startSeconds;

setInterval(() => {
  if (count > 0) {
    count--;
    countdown.innerText = count;
  } else {
    window.location.href = '/fatal';
  }
}, 1000);

countdown.innerText = count;

containerInput.addEventListener('keypress', (event) => {
  if (event.key === 'Enter') {
    const inputValue = containerInput.value;
    if (inputValue === '0x0a0b0c0d0e0f') {
      window.location.href = '/success';
    } else {
      window.location.href = '/fatal';
    }
  }
});