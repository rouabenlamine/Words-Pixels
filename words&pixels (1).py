import sys, requests, difflib, webbrowser
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QFont, QCursor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

PEXELS_API_KEY = "jMQJ64C9phCZDvfqY08F4e9CyF8BQ6WIDJsh2onptWEOibcJ5qn0b0QI"
SEARCH_URL = "https://api.pexels.com/v1/search"

class ImageDownloader(QThread):
    finished = pyqtSignal(QPixmap, str)
    def __init__(self, url, full_url): super().__init__(); self.url, self.full_url = url, full_url
    def run(self):
        r = requests.get(self.url, headers={"Authorization": PEXELS_API_KEY})
        if r.ok:
            pixmap = QPixmap(); pixmap.loadFromData(r.content)
            self.finished.emit(pixmap.scaled(220, 220, Qt.KeepAspectRatio), self.full_url)

class ClickableImage(QLabel):
    def __init__(self, url): 
        super().__init__(); self.url = url; self.setCursor(QCursor(Qt.PointingHandCursor))
    def mousePressEvent(self, e): 
        webbrowser.open(self.url) if e.button() == Qt.LeftButton else None

class ImageSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✨ Image & Document Search ✨"); self.resize(1000, 800)
        self.image_threads = []

        self.searchBar = QLineEdit(); self.searchBar.setPlaceholderText("Enter search keywords...")
        self.searchButton = QPushButton("Search")
        self.searchButton.setStyleSheet("background:#8650B6; color:white; font-weight:bold; padding:5px;")
        self.statusLabel = QLabel("Enter keywords to search for images and documents")

        self.imageLabel = QLabel("🖼️ Relevant Images:"); 
        self.imageLabel.setStyleSheet("font-weight:bold; font-size:14px; color:#8650B6;"); self.imageLabel.hide()
        self.docLabel = QLabel("📄 Relevant Documents:"); 
        self.docLabel.setStyleSheet("font-weight:bold; font-size:14px; color:#8650B6;"); self.docLabel.hide()

        self.imageGridWidget = QWidget(); self.grid = QGridLayout(self.imageGridWidget)
        self.docWidget = QWidget(); self.docLayout = QVBoxLayout(self.docWidget)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h1 style='color:#8650B6;'>✨ Words & Pixels ✨</h1>", alignment=Qt.AlignCenter))
        layout.addWidget(QLabel("<p style='color:#FF9DC5;'>Find beautiful images & relevant papers</p>", alignment=Qt.AlignCenter))
        row = QHBoxLayout(); row.addWidget(self.searchBar, 7); row.addWidget(self.searchButton, 2); layout.addLayout(row)
        layout.addWidget(self.statusLabel)
        layout.addWidget(QFrame(frameShape=QFrame.HLine, styleSheet="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8650B6, stop:1 #FF9DC5); height: 2px;"))

        layout.addWidget(self.imageLabel)
        scroll1 = QScrollArea(); scroll1.setWidgetResizable(True); 
        scroll1.setWidget(self.imageGridWidget); layout.addWidget(scroll1)

        layout.addWidget(self.docLabel)
        scroll2 = QScrollArea(); scroll2.setWidgetResizable(True); 
        scroll2.setWidget(self.docWidget); layout.addWidget(scroll2)

        container = QWidget(); container.setLayout(layout)
        self.setCentralWidget(container)

        self.searchButton.clicked.connect(self.search_all)
        self.searchBar.returnPressed.connect(self.search_all)

    def clear_results(self):
        self.imageLabel.hide(); self.docLabel.hide()
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget: widget.deleteLater()
        for t in self.image_threads: t.quit(); t.wait()
        self.image_threads.clear()

        while self.docLayout.count():
            widget = self.docLayout.takeAt(0).widget()
            if widget: widget.deleteLater()

    def search_all(self):
        query = self.searchBar.text().strip()
        if not query:
            self.statusLabel.setText("Please enter a search term")
            return

        self.clear_results()
        self.statusLabel.setText(f"✨ Searching for '{query}'...")
        self.search_images(query)
        self.search_documents(query)

    def search_images(self, query):
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": 24, "size": "medium"}
        r = requests.get(SEARCH_URL, headers=headers, params=params)
        data = r.json()
        photos = data.get("photos", [])
        if not photos:
            self.statusLabel.setText("✨ No images found")
            return

        self.imageLabel.show()
        self.statusLabel.setText(f"✨ Found {len(photos)} images for '{query}'")
        for i, p in enumerate(photos):
            thumb_url = p['src']['medium']
            full_url = p['url']
            alt = p.get('alt', '')
            similarity = self.similarity_score(query, alt)
            self.add_image_card(i, p['photographer'], full_url, similarity, thumb_url)

    def add_image_card(self, idx, photographer, url, similarity, thumb_url):
        label = ClickableImage(url)
        label.setText("Loading..."); label.setAlignment(Qt.AlignCenter)
        label.setFixedSize(220, 220); label.setStyleSheet("background:#f5f0ff; border:1px solid #e6d8ff;")

        info = QVBoxLayout()
        info.addWidget(QLabel(f"<b>By:</b> {photographer}", styleSheet="color:#8650B6; font-size:11px;"))
        info.addWidget(QLabel(f"<b>Match:</b> {similarity:.1f}%", styleSheet="color:#4A3366;"))
        btn = QPushButton("View Full Image"); btn.setStyleSheet("background:#FF9DC5; color:white; font-size:10px;")
        btn.clicked.connect(lambda: webbrowser.open(url))
        info.addWidget(btn)

        box = QVBoxLayout()
        box.addWidget(label)
        box.addLayout(info)
        card = QWidget(); card.setLayout(box)
        card.setStyleSheet("background:white; border-radius:15px; padding:10px;")

        self.grid.addWidget(card, idx // 4, idx % 4)

        thread = ImageDownloader(thumb_url, url)
        thread.finished.connect(lambda pix, u: label.setPixmap(pix))
        thread.start(); self.image_threads.append(thread)

    def search_documents(self, query):

        url = "https://api.crossref.org/works"

        try:
            r = requests.get(url, params={"query": query, "rows": 10})
            data = r.json()
            items = data.get("message", {}).get("items", [])
            filtered_items = []

            for item in items:
                title = item.get("title", ["Untitled"])[0]
                abstract = item.get("abstract", "")
                similarity = self.similarity_score(query, title + " " + abstract)

                if similarity >= 50.0:
                    filtered_items.append((title, item.get("URL", "#"), similarity))

            if filtered_items:
                self.docLabel.show()
                for title, link, similarity in filtered_items:
                    doc_widget = QWidget()
                    doc_layout = QVBoxLayout()
                    doc_layout.addWidget(QLabel(f"<b>{title}</b>"))
                    doc_layout.addWidget(QLabel(f"<i>Similarity:</i> {similarity:.1f}%"))
                    doc_btn = QPushButton("Open Document")
                    doc_btn.setStyleSheet("background:#A3D2CA; color:#333; font-size:10px;")
                    doc_btn.clicked.connect(lambda _, url=link: webbrowser.open(url))
                    doc_layout.addWidget(doc_btn)

                    doc_widget.setLayout(doc_layout)
                    doc_widget.setStyleSheet("background:#EAF4F4; border-radius:10px; padding:10px;")
                    self.docLayout.addWidget(doc_widget)
            else:
                self.docLabel.show()
                self.docLayout.addWidget(QLabel("📄 No highly relevant documents found."))
        except Exception as e:
            self.docLabel.show()
            self.docLayout.addWidget(QLabel(f"❌ Error fetching documents: {e}"))

    def similarity_score(self, q, text):
        if not text: return 50.0
        q_terms = q.lower().split(); t_terms = text.lower().split()
        score = sum(max(difflib.SequenceMatcher(None, qt, tt).ratio() for tt in t_terms) for qt in q_terms)
        return (score / len(q_terms)) * 100 if q_terms else 50.0

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 10))
    win = ImageSearchApp(); win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
