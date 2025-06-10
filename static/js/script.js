function confirmLogout() {
    // 사용자가 로그아웃을 확인하도록 프롬프트 표시
    return confirm("정말 로그아웃하시겠습니까?");
}

window.onload = function () {
    // 팝업 메시지 입력 요소 가져오기
    const popupInput = document.getElementById("popup-message");
    if (popupInput) {
        // 메시지 값 가져와서 공백 제거
        const message = popupInput.value;
        if (message && message.trim() !== "") {
            // 메시지가 존재하고 비어 있지 않으면 경고창에 표시
            alert(message);
        }
    }
};

function showAlert(msg) {
    // 주어진 메시지를 간단한 경고창으로 표시
    alert(msg);
}