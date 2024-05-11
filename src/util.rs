pub fn remove_prefix(input: String) -> String {
    if input.starts_with("0x") {
        input[2..].to_string()
    } else {
        input
    }
}
