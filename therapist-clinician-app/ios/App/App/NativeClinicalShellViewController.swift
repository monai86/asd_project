import Capacitor
import Network
import UIKit

@objc(NativeClinicalShellViewController)
class NativeClinicalShellViewController: CAPBridgeViewController {
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "clinical.native-shell.network")
    private let loadingView = UIView()
    private let loadingLabel = UILabel()
    private let offlineBanner = UIView()
    private let offlineLabel = UILabel()
    private var isOnline = true

    override var preferredStatusBarStyle: UIStatusBarStyle {
        .darkContent
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        configureWebViewShell()
        configureLoadingView()
        configureOfflineBanner()
        startNetworkMonitor()
        publishShellState(source: "ios-view-did-load")
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        hideLoadingView()
        publishShellState(source: "ios-view-did-appear")
    }

    override func viewSafeAreaInsetsDidChange() {
        super.viewSafeAreaInsetsDidChange()
        publishShellState(source: "ios-safe-area")
    }

    deinit {
        monitor.cancel()
    }

    private func configureWebViewShell() {
        view.backgroundColor = UIColor(red: 0.93, green: 0.99, blue: 1.0, alpha: 1.0)
        webView?.scrollView.contentInsetAdjustmentBehavior = .automatic
        webView?.scrollView.keyboardDismissMode = .interactive
    }

    private func configureLoadingView() {
        loadingView.translatesAutoresizingMaskIntoConstraints = false
        loadingView.backgroundColor = UIColor(red: 0.93, green: 0.99, blue: 1.0, alpha: 1.0)

        loadingLabel.translatesAutoresizingMaskIntoConstraints = false
        loadingLabel.text = "Loading clinical workspace"
        loadingLabel.textAlignment = .center
        loadingLabel.textColor = UIColor(red: 0.05, green: 0.31, blue: 0.39, alpha: 1.0)
        loadingLabel.font = UIFont.preferredFont(forTextStyle: .headline)
        loadingLabel.adjustsFontForContentSizeCategory = true

        loadingView.addSubview(loadingLabel)
        view.addSubview(loadingView)

        NSLayoutConstraint.activate([
            loadingView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            loadingView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            loadingView.topAnchor.constraint(equalTo: view.topAnchor),
            loadingView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            loadingLabel.leadingAnchor.constraint(greaterThanOrEqualTo: loadingView.leadingAnchor, constant: 24),
            loadingLabel.trailingAnchor.constraint(lessThanOrEqualTo: loadingView.trailingAnchor, constant: -24),
            loadingLabel.centerXAnchor.constraint(equalTo: loadingView.centerXAnchor),
            loadingLabel.centerYAnchor.constraint(equalTo: loadingView.centerYAnchor)
        ])
    }

    private func configureOfflineBanner() {
        offlineBanner.translatesAutoresizingMaskIntoConstraints = false
        offlineBanner.backgroundColor = UIColor(red: 1.0, green: 0.95, blue: 0.78, alpha: 1.0)
        offlineBanner.layer.borderColor = UIColor(red: 0.72, green: 0.41, blue: 0.05, alpha: 0.35).cgColor
        offlineBanner.layer.borderWidth = 1
        offlineBanner.layer.cornerRadius = 12
        offlineBanner.isHidden = true
        offlineBanner.accessibilityIdentifier = "native-shell-offline-banner"

        offlineLabel.translatesAutoresizingMaskIntoConstraints = false
        offlineLabel.text = "Offline. Clinical records, uploads, and reports require network access."
        offlineLabel.textColor = UIColor(red: 0.36, green: 0.22, blue: 0.02, alpha: 1.0)
        offlineLabel.font = UIFont.preferredFont(forTextStyle: .footnote)
        offlineLabel.adjustsFontForContentSizeCategory = true
        offlineLabel.numberOfLines = 0

        offlineBanner.addSubview(offlineLabel)
        view.addSubview(offlineBanner)

        NSLayoutConstraint.activate([
            offlineBanner.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 12),
            offlineBanner.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -12),
            offlineBanner.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8),
            offlineLabel.leadingAnchor.constraint(equalTo: offlineBanner.leadingAnchor, constant: 12),
            offlineLabel.trailingAnchor.constraint(equalTo: offlineBanner.trailingAnchor, constant: -12),
            offlineLabel.topAnchor.constraint(equalTo: offlineBanner.topAnchor, constant: 10),
            offlineLabel.bottomAnchor.constraint(equalTo: offlineBanner.bottomAnchor, constant: -10)
        ])
    }

    private func startNetworkMonitor() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                guard let self else { return }
                self.isOnline = path.status == .satisfied
                self.offlineBanner.isHidden = self.isOnline
                self.publishShellState(source: "ios-network")
            }
        }
        monitor.start(queue: monitorQueue)
    }

    private func hideLoadingView() {
        UIView.animate(withDuration: 0.18, delay: 0.05, options: [.curveEaseOut, .allowUserInteraction]) {
            self.loadingView.alpha = 0
        } completion: { _ in
            self.loadingView.isHidden = true
        }
    }

    private func publishShellState(source: String) {
        let safeArea = view.safeAreaInsets
        let payload: [String: Any] = [
            "platform": "ios",
            "source": source,
            "isOnline": isOnline,
            "safeArea": [
                "top": safeArea.top,
                "right": safeArea.right,
                "bottom": safeArea.bottom,
                "left": safeArea.left
            ]
        ]

        guard
            let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
            let json = String(data: data, encoding: .utf8)
        else {
            return
        }

        let script = """
        window.dispatchEvent(new CustomEvent('native-clinical-shell', { detail: \(json) }));
        document.documentElement.dataset.platform = 'ios';
        document.documentElement.dataset.shellStatus = \(isOnline ? "'online'" : "'offline'");
        """
        webView?.evaluateJavaScript(script, completionHandler: nil)
    }
}
