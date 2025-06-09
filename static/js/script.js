function confirmLogout() {
    return confirm("정말 로그아웃하시겠습니까?");
  }

  window.onload = function () {
  const popupInput = document.getElementById("popup-message");
  if (popupInput) {
    const message = popupInput.value;
    if (message && message.trim() !== "") {
      alert(message);
    }
  }
};

function showAlert(msg) {
  alert(msg);
}
