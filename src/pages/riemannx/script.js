(function () {
  var inp = document.getElementById('riemann-input');
  var btn = document.getElementById('riemann-run');
  var out = document.getElementById('riemann-result');

  function millerRabin(n) {
    if (n < 2) return false;
    if (n === 2 || n === 3 || n === 5 || n === 7 || n === 11 || n === 13) return true;
    if (n % 2 === 0 || n % 3 === 0) return false;
    var d = n - 1, r = 0;
    while (d % 2 === 0) { d = Math.floor(d / 2); r++; }
    var witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37];
    for (var wi = 0; wi < witnesses.length; wi++) {
      var a = witnesses[wi];
      if (a >= n) continue;
      var x = modpow(a, d, n);
      if (x === 1 || x === n - 1) continue;
      var cont = false;
      for (var i = 0; i < r - 1; i++) {
        x = mulmod(x, x, n);
        if (x === n - 1) { cont = true; break; }
      }
      if (!cont) return false;
    }
    return true;
  }

  function modpow(base, exp, mod) {
    var result = 1;
    base = base % mod;
    while (exp > 0) {
      if (exp % 2 === 1) result = mulmod(result, base, mod);
      exp = Math.floor(exp / 2);
      base = mulmod(base, base, mod);
    }
    return result;
  }

  function mulmod(a, b, m) {
    var result = 0;
    a = a % m;
    while (b > 0) {
      if (b % 2 === 1) result = (result + a) % m;
      a = (a * 2) % m;
      b = Math.floor(b / 2);
    }
    return result;
  }

  function nearestPrimes(n) {
    var prev = null, next = null;
    for (var k = n - 1; k >= 2; k--) { if (millerRabin(k)) { prev = k; break; } }
    for (var j = n + 1; j <= n + 10000; j++) { if (millerRabin(j)) { next = j; break; } }
    return { prev: prev, next: next };
  }

  function piCount(n) {
    if (n < 2) return { count: 0, exact: true };
    var limit = Math.min(n, 500000);
    var sieve = new Uint8Array(limit + 1).fill(1);
    sieve[0] = sieve[1] = 0;
    for (var i = 2; i * i <= limit; i++) {
      if (sieve[i]) for (var j = i * i; j <= limit; j += i) sieve[j] = 0;
    }
    var count = 0;
    for (var k = 2; k <= limit; k++) { if (sieve[k]) count++; }
    return { count: count, exact: n <= 500000 };
  }

  function run() {
    var n = parseInt(inp.value, 10);
    if (!n || n < 2 || !Number.isFinite(n)) {
      out.textContent = 'Please enter an integer >= 2.';
      out.style.display = 'block';
      return;
    }
    var isPrime = millerRabin(n);
    var near = nearestPrimes(n);
    var pi = piCount(n);
    var approx = n / Math.log(n);
    var nearest = isPrime
      ? n + ' (itself)'
      : (near.prev ? near.prev.toLocaleString() + ' below' : 'none found below') +
        ' / ' +
        (near.next ? near.next.toLocaleString() + ' above' : 'none found above within search cap');
    var lines = [
      'n              : ' + n.toLocaleString(),
      'Is prime       : ' + (isPrime ? 'yes' : 'no'),
      'Nearest prime  : ' + nearest,
      'pi(n) exact    : ' + (pi.exact ? pi.count.toLocaleString() : 'capped at ' + pi.count.toLocaleString() + ' primes through 500,000'),
      'n / log(n)     : about ' + Math.round(approx).toLocaleString()
    ];
    out.textContent = lines.join('\n');
    out.style.display = 'block';
  }

  btn.addEventListener('click', run);
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
}());
