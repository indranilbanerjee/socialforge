// SocialForge Gallery — Filtering and interaction
document.addEventListener('DOMContentLoaded', function() {
  var filters = document.querySelectorAll('.filter');
  var cards = document.querySelectorAll('.card');

  filters.forEach(function(btn) {
    btn.addEventListener('click', function() {
      filters.forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var tier = btn.getAttribute('data-filter');
      cards.forEach(function(card) {
        if (tier === 'all' || card.getAttribute('data-tier') === tier) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
});
