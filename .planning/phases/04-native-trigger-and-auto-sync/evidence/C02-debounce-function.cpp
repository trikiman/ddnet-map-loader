static bool auto_sync_debounce_allows() {
    fs::path marker = auto_sync_marker_path();
    if (marker.empty()) return false;
    std::error_code ec;
    if (!fs::exists(marker, ec)) return true;
    auto last = fs::last_write_time(marker, ec);
    if (ec) return true;  // if we can't read the time, allow the sync
    auto now = decltype(last)::clock::now();
    auto age = std::chrono::duration_cast<std::chrono::seconds>(now - last).count();
    return age >= AUTO_SYNC_DEBOUNCE_SEC;
}