const searchInput = document.getElementById('searchInput');
const productList = document.getElementById('productList');

searchInput.addEventListener('input', () => {
    const searchTerm = searchInput.value.toLowerCase();
    const productCards = productList.querySelectorAll('.card');

    productCards.forEach((card) => {
        const productTitle = card.querySelector('.card-title').textContent.toLowerCase();
        const productDescription = card.querySelector('.card-text').textContent.toLowerCase();

        if (productTitle.includes(searchTerm) || productDescription.includes(searchTerm)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
});
