(function () {
  var inp = document.getElementById('goldbach-input');
  var btn = document.getElementById('goldbach-run');
  var out = document.getElementById('goldbach-result');

  function sieve(limit) {
    var isPrime = new Uint8Array(limit + 1).fill(1);
    isPrime[0] = isPrime[1] = 0;
    for (var i = 2; i * i <= limit; i++) {
      if (isPrime[i]) for (var j = i * i; j <= limit; j += i) isPrime[j] = 0;
    }
    return isPrime;
  }

  function decompose(n) {
    var isPrime = sieve(n);
    var pairs = [];
    for (var p = 2; p <= Math.floor(n / 2); p++) {
      if (isPrime[p] && isPrime[n - p]) pairs.push([p, n - p]);
    }
    return pairs;
  }

  function run() {
    var n = parseInt(inp.value, 10);
    if (!n || n < 4 || n % 2 !== 0) {
      out.textContent = 'Please enter an even integer >= 4.';
      out.style.display = 'block';
      return;
    }
    if (n > 100000) {
      out.textContent = 'Please enter a value <= 100,000 for in-browser computation.';
      out.style.display = 'block';
      return;
    }
    var pairs = decompose(n);
    var lines = [
      'Input          : ' + n.toLocaleString(),
      'Decompositions : ' + pairs.length,
      ''
    ];
    var show = pairs.length <= 20 ? pairs : pairs.slice(0, 20);
    show.forEach(function (p, i) {
      lines.push('  ' + (i + 1) + '.  ' + p[0] + ' + ' + p[1]);
    });
    if (pairs.length > 20) lines.push('  ... and ' + (pairs.length - 20) + ' more pairs');
    out.textContent = lines.join('\n');
    out.style.display = 'block';
  }

  btn.addEventListener('click', run);
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
}());
