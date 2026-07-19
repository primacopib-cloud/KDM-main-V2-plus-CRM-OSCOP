import { FlashPromoBanner } from './FlashPromoBanner';
import { AnnouncementsBanner } from './AnnouncementsBanner';

export const MemberSpaceBanners = ({ space }) => (
  <div className="pt-2">
    <FlashPromoBanner placement="member_spaces" />
    <div className="max-w-7xl mx-auto px-4 mt-3">
      <AnnouncementsBanner space={space} />
    </div>
  </div>
);
