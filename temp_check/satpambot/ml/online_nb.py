from __future__ import annotations







import math







from collections import defaultdict







from typing import Dict, Iterable















class OnlineNB:







    def __init__(self, alpha: float = 1.0):







        self.alpha = alpha







        self.pos_counts = defaultdict(int)







        self.neg_counts = defaultdict(int)







        self.pos_total = 0







        self.neg_total = 0







        self.pos_docs = 0







        self.neg_docs = 0







        self.vocab = set()















    def _update_vocab(self, tokens: Iterable[str]):







        for t in tokens:







            if t:







                self.vocab.add(t)















    def learn(self, tokens: Iterable[str], label: str):







        tokens = [t for t in tokens if t]







        if not tokens:







            return







        self._update_vocab(tokens)







        if label == "phish":







            for t in tokens:







                self.pos_counts[t] += 1







                self.pos_total += 1







            self.pos_docs += 1







        else:







            for t in tokens:







                self.neg_counts[t] += 1







                self.neg_total += 1







            self.neg_docs += 1















    def _log_prob(self, tokens: Iterable[str], label: str) -> float:







        total_docs = self.pos_docs + self.neg_docs







        prior = 0.5 if total_docs == 0 else ((self.pos_docs if label=='phish' else self.neg_docs) / total_docs)







        counts, total = (self.pos_counts, self.pos_total) if label=='phish' else (self.neg_counts, self.neg_total)







        V = max(1, len(self.vocab))







        a = self.alpha







        logp = math.log(prior if prior>0 else 1e-9)







        for t in tokens:







            c = counts.get(t, 0)







            logp += math.log((c + a) / (total + a * V))







        return logp















    def predict_proba(self, tokens: Iterable[str]) -> Dict[str, float]:







        tokens = [t for t in tokens if t]







        if not tokens:







            return {'phish': 0.5, 'safe': 0.5}







        lp_pos = self._log_prob(tokens, 'phish')







        lp_neg = self._log_prob(tokens, 'safe')







        m = max(lp_pos, lp_neg)







        p_pos = math.exp(lp_pos - m)







        p_neg = math.exp(lp_neg - m)







        Z = p_pos + p_neg







        return {'phish': p_pos / Z, 'safe': p_neg / Z}







