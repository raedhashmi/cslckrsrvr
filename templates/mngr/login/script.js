const infobox = document.querySelector('.info-box');
const submit = document.querySelector('.submit-btn');

submit.addEventListener('click', () => {
	const usernameValue = document.querySelector('.username').value.trim();
	const passwordValue = document.querySelector('.password').value.trim();

	infobox.classList.remove('err');
	submit.classList.add('loading');
	submit.disabled = true;

	if (!usernameValue || !passwordValue) {
		setTimeout(() => {
			infobox.classList.add('err');
			infobox.innerHTML = 'Please fill in all of the fields.';
			submit.classList.remove('loading');
			submit.disabled = false;
		}, 200)
	} else {
		setTimeout(() => {
			fetch(`${window.location.origin}/mngr/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					username: usernameValue,
					password: passwordValue,
				}),
			})
			.then((res) => res.json())
			.then((data) => {
				if (data.status === 'success') {
					infobox.classList.add('success');
					infobox.innerHTML = `Successfully logged in.`;
					setTimeout(() => (window.location.href = `${window.location.origin}/mngr`), 1000);
				} else {
					infobox.classList.add('err');
					infobox.innerHTML = data.message;
				}
			})
			.finally(() => {
				submit.classList.remove('loading');
				submit.disabled = false;
			});
		}, Math.random() * (1000 - 500) + 500)
	}
});