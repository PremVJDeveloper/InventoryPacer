import logging
from typing import Dict, List

class RatioCalculator:
    def __init__(self, target_ratios: Dict[str, float]):
        self.target_ratios = target_ratios
        self.logger = logging.getLogger('shopify_tracker')
        
        # Validate ratios sum to 100
        total_ratio = sum(target_ratios.values())
        if abs(total_ratio - 100) > 0.1:
            self.logger.warning(f"Target ratios sum to {total_ratio}%, not 100%")

    def calculate_required_uploads(self, current_counts: Dict[str, int]) -> Dict[str, Dict]:
        """
        Calculate how many products of each type need to be uploaded to maintain target ratios.
        Returns dict containing only product types where more uploads are needed (positive difference).
        """
        total_current = sum(current_counts.values())
        if total_current == 0:
            return {"error": "No products available for analysis"}
        
        # Calculate current percentages
        current_percentages = {}
        for product_type, count in current_counts.items():
            if product_type in self.target_ratios:
                current_percentages[product_type] = (count / total_current) * 100
        
        # Calculate required counts
        required_counts = {}
        for product_type, target_percent in self.target_ratios.items():
            required_count = (target_percent / 100) * total_current
            diff = required_count - current_counts.get(product_type, 0)
            
            # ✅ Keep only positive differences (need to upload more)
            if diff > 0:
                required_counts[product_type] = {
                    'current': current_counts.get(product_type, 0),
                    'required': round(required_count, 2),
                    'next_upload_count': round(diff),  # ← renamed and rounded
                    'current_percent': round(current_percentages.get(product_type, 0), 1),
                    'target_percent': target_percent
                }
        
        if not required_counts:
            self.logger.info("All product categories meet or exceed target ratios.")
        
        return required_counts

    def get_recommendations(self, analysis: Dict[str, Dict]) -> List[str]:
        """Generate upload recommendations for underrepresented types only."""
        recommendations = []
        for product_type, data in analysis.items():
            upload_count = data.get('next_upload_count', 0)
            if upload_count > 0:
                recommendations.append(
                    f"Upload {upload_count} more {product_type} "
                    f"(currently {data['current']}, need total {data['required']:.0f})"
                )
        return recommendations

    def is_ratio_balanced(self, analysis: Dict[str, Dict], tolerance: float = 5.0) -> bool:
        """Check if current ratios are within tolerance of target."""
        for product_type, data in analysis.items():
            if abs(data['current_percent'] - data['target_percent']) > tolerance:
                return False
        return True
