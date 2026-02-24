import 'dart:collection';

/// Pure Dart solver engine ported from functions/main.py
/// All functions here are synchronous and side-effect free.

Map<String, double> calculateLetterFrequency(
  List<String> wordList,
  int length, {
  String? prefix,
}) {
  final filtered = <String>[];
  for (final word in wordList) {
    if (word.length == length && (prefix == null || word.startsWith(prefix))) {
      filtered.add(word);
    }
  }
  if (filtered.isEmpty) return const {};

  final wordsAfterPrefix = prefix == null || prefix.isEmpty
      ? filtered
      : filtered.map((w) => w.substring(prefix.length)).toList(growable: false);

  final frequency = <String, int>{};
  int totalLetters = 0;
  for (final w in wordsAfterPrefix) {
    for (int i = 0; i < w.length; i++) {
      final letter = w[i];
      frequency.update(letter, (v) => v + 1, ifAbsent: () => 1);
      totalLetters += 1;
    }
  }
  if (totalLetters == 0) return const {};

  // Convert to percentage and sort desc
  final Map<String, double> percentage = {
    for (final e in frequency.entries) e.key: (e.value / totalLetters) * 100.0,
  };
  final sorted = SplayTreeMap<String, double>.from(percentage, (a, b) {
    final cmp = percentage[b]!.compareTo(percentage[a]!);
    if (cmp != 0) return cmp;
    return a.compareTo(b);
  });
  return Map<String, double>.fromEntries(sorted.entries);
}

Map<String, double> normalizeLetterFrequencies(
  Map<String, double> frequencies,
) {
  if (frequencies.isEmpty) return const {};
  final values = frequencies.values;
  final maxFreq = values.reduce((a, b) => a > b ? a : b);
  final minFreq = values.reduce((a, b) => a < b ? a : b);
  if (maxFreq == minFreq) {
    return {for (final k in frequencies.keys) k: 5.0};
  }
  return {
    for (final e in frequencies.entries)
      e.key: ((e.value - minFreq) / (maxFreq - minFreq)) * 10.0,
  };
}

double calculateGuessScore(
  String word,
  Map<String, double> letterScores, {
  int guessCount = 1,
}) {
  final countDuplicates = guessCount > 2;
  if (countDuplicates) {
    double sum = 0;
    for (int i = 0; i < word.length; i++) {
      sum += letterScores[word[i]] ?? 0.0;
    }
    return sum;
  }
  // unique letters only
  final seen = <String>{};
  double sum = 0;
  for (int i = 0; i < word.length; i++) {
    final ch = word[i];
    if (seen.add(ch)) {
      sum += letterScores[ch] ?? 0.0;
    }
  }
  return sum;
}

List<String> filterPossibleWords(
  List<String> wordList,
  List<List<(String, String)>> feedbackPerGuess,
) {
  // Flatten by applying constraints iteratively per guess
  var current = wordList;
  for (final guessFeedback in feedbackPerGuess) {
    if (guessFeedback.isEmpty) continue;

    final correctLetterCounts = <String, int>{};
    final presentLetterCounts = <String, int>{};
    for (final (letter, fb) in guessFeedback) {
      correctLetterCounts.putIfAbsent(letter, () => 0);
      presentLetterCounts.putIfAbsent(letter, () => 0);
      if (fb == 'g') {
        correctLetterCounts[letter] = correctLetterCounts[letter]! + 1;
      }
      if (fb == 'y') {
        presentLetterCounts[letter] = presentLetterCounts[letter]! + 1;
      }
    }

    bool isWordPossible(String word) {
      // Build counts per unique letter from the candidate word, once per letter
      final wordLetterCounts = <String, int>{};
      for (final (letter, _) in guessFeedback) {
        if (!wordLetterCounts.containsKey(letter)) {
          int count = 0;
          for (int i = 0; i < word.length; i++) {
            if (word[i] == letter) count++;
          }
          wordLetterCounts[letter] = count;
        }
      }
      for (int i = 0; i < guessFeedback.length; i++) {
        final (letter, fb) = guessFeedback[i];
        if (fb == 'g') {
          if (word[i] != letter ||
              (wordLetterCounts[letter] ?? 0) <
                  (correctLetterCounts[letter] ?? 0)) {
            return false;
          }
        } else if (fb == 'y') {
          if (!word.contains(letter) ||
              word[i] == letter ||
              (wordLetterCounts[letter] ?? 0) <=
                  (correctLetterCounts[letter] ?? 0)) {
            return false;
          }
        } else if (fb == 'b') {
          if (word.contains(letter) &&
              (wordLetterCounts[letter] ?? 0) >
                  (correctLetterCounts[letter] ?? 0) +
                      (presentLetterCounts[letter] ?? 0)) {
            return false;
          }
        }
      }
      return true;
    }

    current = current.where(isWordPossible).toList(growable: false);
  }
  return current;
}

List<(String, double)> recommendGuesses(
  List<String> wordList,
  int length,
  String? prefix, {
  int n = 9,
  int guessCount = 1,
  List<String>? scoreBaseWordList,
}) {
  final filtered = <String>[];
  for (final word in wordList) {
    if (word.length == length && (prefix == null || word.startsWith(prefix))) {
      filtered.add(word);
    }
  }
  if (filtered.isEmpty) return const [];

  final base = scoreBaseWordList ?? wordList;
  final frequencies = calculateLetterFrequency(base, length, prefix: prefix);
  final letterScores = normalizeLetterFrequencies(frequencies);

  final scored = <(String, double)>[];
  for (final w in filtered) {
    final s = calculateGuessScore(w, letterScores, guessCount: guessCount);
    scored.add((w, s));
  }
  scored.sort((a, b) => b.$2.compareTo(a.$2));
  return scored.take(n).toList(growable: false);
}

Map<int, Set<String>> findVariableLetterPositions(List<String> wordList) {
  if (wordList.isEmpty) return const {};
  final length = wordList.first.length;
  final variable = {for (int i = 0; i < length; i++) i: <String>{}};
  for (final w in wordList) {
    for (int i = 0; i < w.length && i < length; i++) {
      variable[i]!.add(w[i]);
    }
  }
  return Map.fromEntries(variable.entries.where((e) => e.value.length > 1));
}

Map<String, dynamic> computeNextMove({
  required List<String> dictionary,
  required int wordLength,
  required String? prefix,
  required List<Map<String, String>> history, // [{guess, feedback}]
}) {
  // Seed candidates by length/prefix
  List<String> possibleWords = [
    for (final w in dictionary)
      if (w.length == wordLength && (prefix == null || w.startsWith(prefix))) w,
  ];

  // Apply history
  final feedbackPerGuess = <List<(String, String)>>[];
  for (final entry in history) {
    final guess = (entry['guess'] ?? '').toLowerCase();
    final fb = (entry['feedback'] ?? '').toLowerCase();
    if (guess.length != wordLength || fb.length != wordLength) {
      throw ArgumentError(
        'Invalid history entry: expected guess/feedback length $wordLength, '
        'got guess=${guess.length}, feedback=${fb.length}.',
      );
    }
    // Validate feedback characters up-front to avoid positional drift
    for (int i = 0; i < wordLength; i++) {
      final c = fb[i];
      if (c != 'g' && c != 'y' && c != 'b') {
        throw ArgumentError(
          "Invalid feedback character at index $i: '$c' (allowed: g,y,b)",
        );
      }
    }
    final pairs = <(String, String)>[];
    for (int i = 0; i < wordLength; i++) {
      final c = fb[i];
      pairs.add((guess[i], c));
    }
    feedbackPerGuess.add(pairs);
  }
  possibleWords = filterPossibleWords(possibleWords, feedbackPerGuess);

  final guessCount = history.length + 1;
  final recs = recommendGuesses(
    possibleWords,
    wordLength,
    prefix,
    n: 9,
    guessCount: guessCount,
    scoreBaseWordList: dictionary,
  );

  final variablePositions = findVariableLetterPositions(possibleWords);
  final variableLetters = <String>{};
  for (final s in variablePositions.values) {
    variableLetters.addAll(s);
  }

  final fillerSuggestions = <String>[];
  if (variableLetters.isNotEmpty && possibleWords.length > 10) {
    final candidates = <String>[];
    for (final w in dictionary) {
      if (w.length == wordLength && variableLetters.any((l) => w.contains(l))) {
        candidates.add(w);
      }
    }
    final scored = <(String, int)>[];
    final uniqueVars = variableLetters.toSet();
    for (final w in candidates) {
      int score = 0;
      for (final l in uniqueVars) {
        if (w.contains(l)) score += 1;
      }
      scored.add((w, score));
    }
    scored.sort((a, b) => b.$2.compareTo(a.$2));
    for (final t in scored.take(9)) {
      fillerSuggestions.add(t.$1);
    }
  }

  final formattedVariable = {
    for (final e in variablePositions.entries)
      e.key.toString(): e.value.toList(),
  };

  return {
    'recommendations': [
      for (final t in recs)
        {'word': t.$1, 'score': double.parse(t.$2.toStringAsFixed(2))},
    ],
    'remainingWords': possibleWords.take(100).toList(),
    'remainingCount': possibleWords.length,
    'variablePositions': formattedVariable,
    'fillerSuggestions': fillerSuggestions,
    'guessCount': guessCount,
  };
}
