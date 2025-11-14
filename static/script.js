document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");

  form.addEventListener("submit", (event) => {
    // Можно добавить простую проверку перед отправкой
    const username = form.querySelector("input[name='name']").value.trim();
    const password = form.querySelector("input[name='password']").value.trim();

    if (!username || !password) {
      event.preventDefault();
      alert("Заполните все поля!");
    }
  });
});
