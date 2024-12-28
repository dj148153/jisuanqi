#include <vector>
#include <string>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <limits>

std::string vectorToString(const std::vector<double>& vec) {
    if (vec.empty()) return "";
    
    std::ostringstream oss;
    // 设置使用科学计数法并保留最大有效数字
    oss << std::scientific 
        << std::setprecision(std::numeric_limits<double>::max_digits10);
    
    for (size_t i = 0; i < vec.size(); ++i) {
        oss << vec[i];
        if (i < vec.size() - 1) {
            oss << ",";
        }
    }
    
    return oss.str();
}

// 测试代码
int main() {
    std::vector<double> numbers = {1.23456789, 2.0, 3.14159, 0.000123456789};
    std::string result = vectorToString(numbers);
    std::cout << result << std::endl;
    return 0;
} 