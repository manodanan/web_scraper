#!/usr/bin/env python3
"""
Backend API Machine Learning Classifier
----------------------------------------
Implements a multi-feature Scikit-Learn pipeline (TF-IDF sublinear n-grams +
structural & domain feature extraction + Calibrated Gradient Boosting)
to classify network endpoints as core application backend APIs vs 3rd-party noise.
"""

import os
import re
import math
import joblib
from urllib.parse import urlparse, parse_qs
import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline, FeatureUnion


TRAINING_CORPUS = [
    # Positive Examples (Label 1)
    {"url": "https://apigw.trendyol.com/devx-extensibility-ring-api/v1/rings/evaluate", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://demeter-api.trendyol.com/c/int/core/custom_parameters", "method": "GET", "type": "fetch", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://demeter-api.trendyol.com/c/int/core/ea", "method": "POST", "type": "ping", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://api.hepsiburada.com/v1/product/detail?id=123", "method": "GET", "type": "xhr", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://www.hepsiburada.com/api/checkout/summary", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://dummyjson.com/products", "method": "GET", "type": "fetch", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://dummyjson.com/users/1", "method": "GET", "type": "xhr", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://dummyjson.com/carts/add", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://dummyjson.com/posts/search?q=love", "method": "GET", "type": "fetch", "headers": {}, "label": 1},
    {"url": "https://api.example.com/v1/products/list", "method": "GET", "type": "xhr", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://www.example.com/api/v2/user/cart", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://example.com/graphql", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://api.example.com/search?q=phone&category=electronics", "method": "GET", "type": "xhr", "headers": {}, "label": 1},
    {"url": "https://example.com/api/checkout/pay", "method": "POST", "type": "fetch", "headers": {"authorization": "Bearer token123"}, "label": 1},
    {"url": "https://catalog-service.example.com/items/details", "method": "GET", "type": "fetch", "headers": {"accept": "application/json"}, "label": 1},
    {"url": "https://example.com/v1/auth/login", "method": "POST", "type": "fetch", "headers": {"content-type": "application/json"}, "label": 1},
    {"url": "https://example.com/api/user/profile", "method": "GET", "type": "fetch", "headers": {"authorization": "Bearer token123"}, "label": 1},
    {"url": "https://backend.example.com/rest/orders/123", "method": "GET", "type": "xhr", "headers": {}, "label": 1},

    # Negative Examples (Label 0)
    {"url": "https://www.google-analytics.com/g/collect?v=2&tid=G-12345", "method": "POST", "type": "fetch", "headers": {}, "label": 0},
    {"url": "https://fundingchoicesmessages.google.com/el/AGSKWxU56", "method": "POST", "type": "xhr", "headers": {}, "label": 0},
    {"url": "https://connect.facebook.net/en_US/fbevents.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://cdn.example.com/assets/app.main.css", "method": "GET", "type": "stylesheet", "headers": {}, "label": 0},
    {"url": "https://example.com/cdn-cgi/rum?", "method": "POST", "type": "xhr", "headers": {}, "label": 0},
    {"url": "https://www.googletagmanager.com/gtm.js?id=GTM-1234", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://static.cloudflareinsights.com/beacon.min.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://static.example.com/images/logo.png", "method": "GET", "type": "image", "headers": {}, "label": 0},
    {"url": "https://script.hotjar.com/modules.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://browser.sentry-cdn.com/7.0.0/bundle.min.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://adservice.google.com/adsid/google/ui", "method": "GET", "type": "xhr", "headers": {}, "label": 0},
    {"url": "https://stats.g.doubleclick.net/r/collect", "method": "POST", "type": "fetch", "headers": {}, "label": 0},
    {"url": "https://example.com/favicon.ico", "method": "GET", "type": "other", "headers": {}, "label": 0},
    {"url": "https://fonts.googleapis.com/css2?family=Roboto", "method": "GET", "type": "stylesheet", "headers": {}, "label": 0},
    {"url": "https://analytics.tiktok.com/i18n/pixel/events.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://cdn.dsmcdn.com/sfx/mergen/0.13.1/index.js", "method": "GET", "type": "script", "headers": {}, "label": 0},
    {"url": "https://www.trendyol.com/en/select-country", "method": "GET", "type": "document", "headers": {}, "label": 0}
]


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
    return - sum([p * math.log(p, 2) for p in prob])


class EndpointFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, target_host=""):
        self.target_host = target_host.lower()

    def set_target_host(self, target_url: str):
        parsed = urlparse(target_url)
        self.target_host = parsed.netloc.lower().replace("www.", "")

    def fit(self, X, y=None):
        return self

    def _extract_single(self, item):
        if isinstance(item, str):
            url = item
            method = "GET"
            res_type = "other"
            headers = {}
        elif isinstance(item, dict):
            url = item.get("url", "")
            method = item.get("method", "GET").upper()
            res_type = item.get("type", "other").lower()
            headers = item.get("headers", {})
        else:
            url = str(item)
            method = "GET"
            res_type = "other"
            headers = {}

        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
        query = parsed.query.lower()

        # Domain Affinity
        if self.target_host:
            if host == self.target_host or host.endswith("." + self.target_host):
                domain_affinity = 1.0
            elif any(part in host for part in self.target_host.split('.')) and len(self.target_host) > 4:
                domain_affinity = 0.8
            else:
                domain_affinity = 0.0
        else:
            domain_affinity = 0.5

        # Path Segment Count & Entropy
        path_segments = [s for s in path.split('/') if s]
        segment_count = float(len(path_segments))
        path_entropy = _shannon_entropy(path)

        # Digit Ratio
        digits = sum(c.isdigit() for c in path)
        digit_ratio = (float(digits) / len(path)) if len(path) > 0 else 0.0

        # Query Params
        query_params = parse_qs(query)
        param_count = float(len(query_params))

        # Request Type (fetch / xhr / ping)
        is_xhr_fetch = 1.0 if res_type in ["xhr", "fetch", "ping", "websocket"] else 0.0
        is_mutating = 1.0 if method in ["POST", "PUT", "DELETE", "PATCH"] else 0.0

        # Headers
        headers_str = str(headers).lower()
        is_json_header = 1.0 if ("application/json" in headers_str or "graphql" in headers_str) else 0.0
        has_auth_header = 1.0 if ("authorization" in headers_str or "x-api-key" in headers_str or "bearer" in headers_str) else 0.0

        # Keywords
        api_keywords = ['api', 'v1', 'v2', 'v3', 'graphql', 'rest', 'service', 'gateway', 'query', 'mutation', 'rpc', 'ring', 'evaluate', 'core', 'custom_parameters', 'cart', 'checkout', 'product', 'products', 'users', 'posts', 'comments', 'auth', 'item', 'search', 'catalog']
        has_api_keyword = 1.0 if any(kw in path or kw in host for kw in api_keywords) else 0.0

        noise_keywords = ['analytics', 'telemetry', 'collect', 'pixel', 'rum', 'sentry', 'hotjar', 'gtm', 'facebook', 'doubleclick', 'adservice', 'googlesyndication', 'cloudflareinsights', 'beacon', 'static', 'assets', 'css', 'js', 'png', 'jpg', 'svg', 'woff', 'select-country']
        has_noise_keyword = 1.0 if any(kw in path or kw in host for kw in noise_keywords) else 0.0

        # Static file extension penalty
        static_exts = ['.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.ico', '.woff', '.ttf']
        is_static_ext = 1.0 if any(path.endswith(ext) for ext in static_exts) else 0.0

        return [
            domain_affinity,
            segment_count,
            path_entropy,
            digit_ratio,
            param_count,
            is_xhr_fetch,
            is_mutating,
            is_json_header,
            has_auth_header,
            has_api_keyword,
            has_noise_keyword,
            is_static_ext
        ]

    def transform(self, X):
        return np.array([self._extract_single(item) for item in X])


class MLBackendClassifier:
    """
    Production Machine Learning Classifier for API endpoints.
    """
    MODEL_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".model_cache.joblib")

    def __init__(self, target_host=""):
        self.feature_extractor = EndpointFeatureExtractor(target_host=target_host)
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(3, 5),
            sublinear_tf=True
        )
        self.classifier = CalibratedClassifierCV(
            estimator=GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.08,
                max_depth=3,
                random_state=42
            ),
            cv=3
        )
        self._is_trained = False
        self._train_model()

    def set_target_host(self, target_url: str):
        self.feature_extractor.set_target_host(target_url)

    def _extract_url_string(self, item):
        if isinstance(item, dict):
            return item.get("url", "")
        return str(item)

    def _train_model(self):
        X_items = [item for item in TRAINING_CORPUS]
        X_urls = [self._extract_url_string(item) for item in TRAINING_CORPUS]
        y_labels = [item["label"] for item in TRAINING_CORPUS]

        tfidf_mat = self.vectorizer.fit_transform(X_urls).toarray()
        struct_mat = self.feature_extractor.transform(X_items)
        X_combined = np.hstack((tfidf_mat, struct_mat))

        self.classifier.fit(X_combined, y_labels)
        self._is_trained = True

    def predict_score(self, item) -> float:
        if not self._is_trained:
            self._train_model()

        url_str = self._extract_url_string(item)
        method = item.get("method", "GET").upper() if isinstance(item, dict) else "GET"
        res_type = item.get("type", "other").lower() if isinstance(item, dict) else "other"

        tfidf_feat = self.vectorizer.transform([url_str]).toarray()
        struct_feat = self.feature_extractor.transform([item])

        X_test = np.hstack((tfidf_feat, struct_feat))
        probs = self.classifier.predict_proba(X_test)[0]
        score = probs[1] if len(probs) > 1 else probs[0]

        parsed = urlparse(url_str)
        host = parsed.netloc.lower()

        # Hard penalty for static JS/CSS/Font assets
        if any(parsed.path.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.svg', '.woff', '.ttf', '.ico']):
            score = min(score, 0.10)

        # Hard penalty for known analytics / tracker domains
        if any(tracker in host for tracker in ['google-analytics', 'googletagmanager', 'googlesyndication', 'cloudflareinsights', 'hotjar', 'facebook', 'sentry', 'doubleclick', 'tiktok']):
            score = min(score, 0.05)

        # Boost for subdomains or paths with API / Gateway indicators on target domain
        target_host = self.feature_extractor.target_host
        if target_host and (host == target_host or host.endswith("." + target_host)):
            if res_type in ["fetch", "xhr", "ping"] or any(k in parsed.path for k in ['/api/', '/v1/', '/v2/', '/graphql', '/service/', '/products', '/users', '/carts', '/posts']):
                if not any(parsed.path.endswith(ext) for ext in ['.js', '.css']):
                    score = max(score, 0.85)

        return round(float(score), 4)


if __name__ == "__main__":
    clf = MLBackendClassifier(target_host="dummyjson.com")
    sample = {"url": "https://dummyjson.com/products", "method": "GET", "type": "fetch"}
    print("Sample Score:", clf.predict_score(sample))
